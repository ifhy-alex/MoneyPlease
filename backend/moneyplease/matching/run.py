import logging
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import exists, select
from sqlalchemy.orm import sessionmaker

from moneyplease.db.models import Job, Match, MatchRun
from moneyplease.matching.embed import Embedder, job_text
from moneyplease.matching.filters import passes
from moneyplease.matching.llm import LLMError, LLMProvider, QuotaExceeded
from moneyplease.matching.score import evaluate, to_row
from moneyplease.profile import store
from moneyplease.profile.schema import Profile

log = logging.getLogger(__name__)
BATCH = 64
PRESELECT = 400


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
    run.embebidas = _embed_missing(session_factory, embedder)

    with session_factory() as s:
        already = exists().where(Match.profile_id == profile_id, Match.job_id == Job.id)
        pre = s.scalars(select(Job).where(Job.estado == "active", Job.embedding.is_not(None), ~already)
                        .order_by(Job.embedding.cosine_distance(vector)).limit(PRESELECT)).all()
        candidates = [j for j in pre if passes(j, profile.preferences)]
        run.candidatas = len(candidates)
        s.expunge_all()

    for job in candidates[:top_k][:max_evals]:
        try:
            result = evaluate(llm, profile, job)
        except QuotaExceeded:
            log.warning("Cuota del LLM agotada; lo pendiente se evalúa en la próxima corrida")
            run.cuota_agotada = True
            break
        except LLMError as exc:
            log.warning("Oferta %s: %s", job.id, exc)
            run.fallidas += 1
            continue
        except Exception:
            log.exception("Oferta %s: error inesperado al evaluar", job.id)
            run.fallidas += 1
            continue
        with session_factory() as s:
            s.add(to_row(profile_id, job.id, result, llm.model, now()))
            s.commit()
        run.evaluadas += 1

    run.terminado_en = now()
    with session_factory() as s:
        s.add(run)
        s.commit()
    log.info("Matching: embebidas=%d candidatas=%d evaluadas=%d fallidas=%d cuota_agotada=%s",
             run.embebidas, run.candidatas, run.evaluadas, run.fallidas, run.cuota_agotada)
    return run
