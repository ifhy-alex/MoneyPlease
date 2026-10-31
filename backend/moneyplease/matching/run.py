import logging
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import exists, or_, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, defer, sessionmaker

from moneyplease.db.models import Job, Match, MatchFailure, MatchRun
from moneyplease.eval import top_matches
from moneyplease.matching.embed import Embedder, job_text
from moneyplease.matching.examples import Ejemplo, select_examples
from moneyplease.matching.filters import passes
from moneyplease.matching.llm import LLMError, LLMProvider, QuotaExceeded
from moneyplease.matching.score import evaluate, to_row
from moneyplease.profile import store
from moneyplease.profile.schema import Preferences, Profile

log = logging.getLogger(__name__)
BATCH = 64
PRESELECT = 2000
MAX_CONSECUTIVE_ERRORS = 3
MAX_FAILURES_PER_JOB = 3
MAX_REEVALUATIONS = 10


def utcnow() -> datetime:
    return datetime.now(UTC)


def _embed_missing(session_factory: sessionmaker, embedder: Embedder) -> int:
    total = 0
    while True:
        with session_factory() as s:
            batch = s.scalars(select(Job).where(Job.estado == "active", Job.embedding.is_(None))
                              .order_by(Job.id).limit(BATCH)).all()
            if not batch:
                return total
            for job, vector in zip(batch, embedder.embed([job_text(j) for j in batch])):
                job.embedding = vector
            s.commit()
            total += len(batch)


def _preselect(session: Session, profile_id: int, vector, remoto_abierto: bool) -> list[Job]:
    # Con el índice HNSW, pgvector filtra después del escaneo y ef_search corta las filas: con filtros
    # puede devolver muy pocas. Un escaneo exacto de unas miles de ofertas cuesta milisegundos.
    session.execute(text("SET LOCAL enable_indexscan = off"))
    already = exists().where(Match.profile_id == profile_id, Match.job_id == Job.id)
    # Ofertas que fallaron demasiadas veces con este perfil: no gastar más llamadas en ellas.
    given_up = exists().where(MatchFailure.profile_id == profile_id, MatchFailure.job_id == Job.id,
                              MatchFailure.intentos >= MAX_FAILURES_PER_JOB)
    # Filtro barato en SQL antes de ordenar: si no, las ofertas parecidas pero de otros países
    # llenan la ventana de preselección y tapan a las que sí aplican.
    place = or_(Job.pais == "CR", Job.modalidad == "remoto") if remoto_abierto else Job.pais == "CR"
    return list(session.scalars(select(Job).options(defer(Job.raw_json))
                                .where(Job.estado == "active", Job.embedding.is_not(None), ~already,
                                       ~given_up, place)
                                .order_by(Job.embedding.cosine_distance(vector)).limit(PRESELECT)).all())


def pending_candidates(session: Session, profile_id: int, vector, prefs: Preferences) -> list[Job]:
    """Ofertas que pasarían los filtros y aún no se evaluaron con este perfil (sin llamar al LLM)."""
    return [j for j in _preselect(session, profile_id, vector, prefs.remoto_abierto) if passes(j, prefs)]


def _record_failure(session_factory: sessionmaker, profile_id: int, job_id: int, error: str,
                    now: datetime) -> None:
    stmt = insert(MatchFailure).values(profile_id=profile_id, job_id=job_id, intentos=1,
                                       ultimo_error=error[:500], actualizado_en=now)
    stmt = stmt.on_conflict_do_update(
        index_elements=["profile_id", "job_id"],
        set_={"intentos": MatchFailure.intentos + 1, "ultimo_error": stmt.excluded.ultimo_error,
              "actualizado_en": stmt.excluded.actualizado_en})
    with session_factory() as s:
        s.execute(stmt)
        s.commit()


def _evaluate_candidates(session_factory: sessionmaker, llm: LLMProvider, profile: Profile, profile_id: int,
                         candidates: list[Job], run: MatchRun, now: Callable[[], datetime],
                         ejemplos: list[Ejemplo] | None = None, ejemplos_hash: str | None = None,
                         reevaluation: bool = False) -> bool:
    """Evalúa en orden; devuelve False si la corrida debe cortarse (cuota o errores seguidos)."""
    consecutive_errors = 0
    for job in candidates:
        try:
            result = evaluate(llm, profile, job, ejemplos)
        except QuotaExceeded:
            log.warning("Cuota del LLM agotada; lo pendiente se evalúa en la próxima corrida")
            run.cuota_agotada = True
            return False
        except LLMError as exc:
            # El proveedor respondió (aunque mal): no cuenta como caída de red.
            log.warning("Oferta %s: %s", job.id, exc)
            run.fallidas += 1
            consecutive_errors = 0
            _record_failure(session_factory, profile_id, job.id, str(exc), now())
            continue
        except Exception as exc:
            log.exception("Oferta %s: error inesperado al evaluar", job.id)
            run.fallidas += 1
            consecutive_errors += 1
            _record_failure(session_factory, profile_id, job.id, f"{type(exc).__name__}: {exc}", now())
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                # Probablemente la red o el proveedor están caídos: no bloquear el worker con más timeouts.
                run.error = f"corrida cortada tras {consecutive_errors} errores seguidos (red o proveedor): {exc}"
                return False
            continue
        consecutive_errors = 0
        with session_factory() as s:
            s.merge(to_row(profile_id, job.id, result, llm.model, now(), ejemplos_hash))
            s.commit()
        if reevaluation:
            run.reevaluadas += 1
        else:
            run.evaluadas += 1
    return True


def _stale_top(session_factory: sessionmaker, profile_id: int, ejemplos: list[Ejemplo],
               ejemplos_hash: str | None) -> list[Job]:
    """Ofertas del top evaluadas con otro conjunto de ejemplos (sin contar las que son ejemplo)."""
    example_ids = {e.job_id for e in ejemplos}
    with session_factory() as s:
        stale = [job for match, job in top_matches(s, profile_id, 10)
                 if match.ejemplos_hash != ejemplos_hash and job.id not in example_ids]
        s.expunge_all()
    return stale[:MAX_REEVALUATIONS]


def run_match(session_factory: sessionmaker, embedder: Embedder, llm: LLMProvider, *, top_k: int = 40,
              max_evals: int = 50, now: Callable[[], datetime] = utcnow) -> MatchRun | None:
    with session_factory() as s:
        row = store.active(s)
        if row is None:
            log.info("Sin perfil guardado; matching omitido")
            return None
        profile_id, vector = row.id, row.embedding
        profile = Profile.model_validate(row.perfil_json)

    run = MatchRun(profile_id=profile_id, iniciado_en=now(), embebidas=0, candidatas=0, evaluadas=0,
                   fallidas=0, cuota_agotada=False)
    run.reevaluadas = 0  # solo para el log y quien llama; no tiene columna
    try:
        run.embebidas = _embed_missing(session_factory, embedder)
        with session_factory() as s:
            candidates = pending_candidates(s, profile_id, vector, profile.preferences)
            run.candidatas = len(candidates)
            s.expunge_all()
        # Un --limit mayor que top_k amplía la ventana en lugar de quedar topeado en silencio.
        window = max(top_k, max_evals)
        with session_factory() as s:
            ejemplos, ejemplos_hash = select_examples(s, profile_id)
        ok = _evaluate_candidates(session_factory, llm, profile, profile_id, candidates[:window][:max_evals], run,
                                  now, ejemplos, ejemplos_hash)
        if ok:
            # Si cambiaron las etiquetas, el top se vuelve a evaluar con los ejemplos nuevos.
            stale = _stale_top(session_factory, profile_id, ejemplos, ejemplos_hash)
            _evaluate_candidates(session_factory, llm, profile, profile_id, stale, run, now, ejemplos,
                                 ejemplos_hash, reevaluation=True)
    except Exception as exc:  # la corrida siempre queda registrada, aunque falle a medio camino
        log.exception("Matching: la corrida falló")
        run.error = f"{type(exc).__name__}: {exc}"
    finally:
        run.terminado_en = now()
        with session_factory() as s:
            s.add(run)
            s.commit()
    log.info("Matching: embebidas=%d candidatas=%d evaluadas=%d reevaluadas=%d fallidas=%d cuota_agotada=%s",
             run.embebidas, run.candidatas, run.evaluadas, run.reevaluadas, run.fallidas, run.cuota_agotada)
    return run
