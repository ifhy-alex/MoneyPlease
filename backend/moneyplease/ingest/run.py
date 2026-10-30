import logging
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import case, literal_column, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from moneyplease.config import Settings
from moneyplease.db.models import IngestRun, Job, Source
from moneyplease.ingest.base import Connector, QuotaExhausted, SourceGone
from moneyplease.ingest.connectors import build_connector
from moneyplease.ingest.http import PoliteClient
from moneyplease.ingest.normalize import normalize
from moneyplease.ingest.sources import sync

log = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(UTC)


def _record_failure(session: Session, source: Source, run: IngestRun, exc: Exception) -> None:
    if isinstance(exc, SourceGone):
        source.activa, source.desactivada_motivo = False, str(exc)
    if isinstance(exc, QuotaExhausted):
        source.config_json = {**source.config_json, "quota_exhausted_until": exc.until.isoformat()}
    run.ok, run.error = False, f"{type(exc).__name__}: {exc}"


def _store(session: Session, source: Source, conn: Connector, jobs: list, ts: datetime) -> int:
    rows = {}
    for raw in jobs:
        row = normalize(raw)
        rows[row["hash"]] = row  # la última aparición gana
    nuevas = 0
    for row in rows.values():
        stmt = insert(Job).values(source_id=source.id, estado="active", corridas_ausente=0,
                                  primera_vez_visto=ts, ultima_vez_visto=ts, **row)
        stmt = stmt.on_conflict_do_update(
            index_elements=["hash"],
            set_={"ultima_vez_visto": ts, "raw_json": stmt.excluded.raw_json,
                  "descripcion": stmt.excluded.descripcion, "corridas_ausente": 0, "estado": "active"},
        ).returning(literal_column("xmax = 0"))
        if session.execute(stmt).scalar():
            nuevas += 1
    if conn.is_complete_listing:
        session.execute(
            update(Job)
            .where(Job.source_id == source.id, Job.estado == "active", Job.hash.not_in(list(rows)))
            .values(corridas_ausente=Job.corridas_ausente + 1,
                    estado=case((Job.corridas_ausente + 1 >= 2, "expired"), else_=Job.estado))
        )
    return nuevas


def _run_source(session_factory: sessionmaker, source_id: int, conn: Connector,
                now: Callable[[], datetime]) -> IngestRun:
    started = now()
    log.info("Fuente %s: inicio", conn.key)
    try:
        result = conn.fetch()
    except Exception as exc:  # un conector roto nunca detiene a los demás
        log.warning("Fuente %s: falló el fetch: %s", conn.key, exc)
        with session_factory() as s:
            source = s.get(Source, source_id)
            run = IngestRun(source_id=source_id, iniciado_en=started, ofertas_traidas=0, ofertas_nuevas=0)
            _record_failure(s, source, run, exc)
            run.terminado_en = now()
            s.add(run)
            s.commit()
            return run
    with session_factory() as s:
        source = s.get(Source, source_id)
        run = IngestRun(source_id=source_id, iniciado_en=started, ofertas_traidas=len(result.jobs))
        try:
            run.ofertas_nuevas = _store(s, source, conn, result.jobs, now())
            if result.config_updates:
                source.config_json = {**source.config_json, **result.config_updates}
            run.ok = True
        except Exception as exc:
            log.exception("Fuente %s: falló al guardar", conn.key)
            s.rollback()
            source = s.get(Source, source_id)
            run.ok, run.ofertas_nuevas, run.error = False, 0, f"{type(exc).__name__}: {exc}"
        run.terminado_en = now()
        s.add(run)
        s.commit()
    log.info("Fuente %s: ok=%s traídas=%d nuevas=%d", conn.key, run.ok, run.ofertas_traidas, run.ofertas_nuevas)
    return run


def run_ingest(session_factory: sessionmaker, settings: Settings, *, only: str | None = None,
               exclude: set[str] | None = None, connector_factory=build_connector,
               now: Callable[[], datetime] = utcnow) -> list[IngestRun]:
    with session_factory() as s:
        sync(s, settings)
        sources = s.scalars(select(Source).where(Source.activa).order_by(Source.id)).all()
    client = PoliteClient()
    today = now().date()
    runs = []
    for source in sources:
        if (only and source.key != only) or (exclude and source.key in exclude):
            continue
        conn = connector_factory(source, settings, client, today)
        if conn is None:
            continue
        runs.append(_run_source(session_factory, source.id, conn, now))
    return runs
