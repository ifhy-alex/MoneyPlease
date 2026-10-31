from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from moneyplease.db.models import IngestRun, Job, MatchRun, Source


@dataclass
class SourceStats:
    key: str
    activa: bool
    ofertas_activas: int
    nuevas_24h: int
    en_cr: int
    ultima_corrida_ok: bool | None
    ultima_corrida_en: datetime | None
    cero_en_dos_ultimas: bool


def collect(session: Session, now: datetime) -> list[SourceStats]:
    active = Job.estado == "active"
    counts = {
        sid: (total, nuevas, cr)
        for sid, total, nuevas, cr in session.execute(
            select(Job.source_id,
                   func.count().filter(active),
                   func.count().filter(active, Job.primera_vez_visto >= now - timedelta(hours=24)),
                   func.count().filter(active, Job.pais == "CR"))
            .group_by(Job.source_id))
    }
    rows = []
    for src in session.scalars(select(Source).order_by(Source.key)):
        last = session.scalars(select(IngestRun).where(IngestRun.source_id == src.id)
                               .order_by(IngestRun.iniciado_en.desc()).limit(1)).first()
        last_ok = session.scalars(select(IngestRun.ofertas_traidas)
                                  .where(IngestRun.source_id == src.id, IngestRun.ok)
                                  .order_by(IngestRun.iniciado_en.desc()).limit(2)).all()
        total, nuevas, cr = counts.get(src.id, (0, 0, 0))
        rows.append(SourceStats(
            key=src.key, activa=src.activa, ofertas_activas=total, nuevas_24h=nuevas, en_cr=cr,
            ultima_corrida_ok=last.ok if last else None,
            ultima_corrida_en=last.iniciado_en if last else None,
            cero_en_dos_ultimas=len(last_ok) == 2 and not any(last_ok),
        ))
    return rows


@dataclass
class MatchStatus:
    last: MatchRun | None
    sin_embedding: int
    pendientes: int | None = None  # None: no hay perfil guardado


def match_status(session: Session) -> MatchStatus:
    from moneyplease.matching.run import pending_candidates
    from moneyplease.profile import store
    from moneyplease.profile.schema import Profile

    last = session.scalars(select(MatchRun).order_by(MatchRun.iniciado_en.desc()).limit(1)).first()
    sin_embedding = session.scalar(select(func.count()).select_from(Job)
                                   .where(Job.estado == "active", Job.embedding.is_(None)))
    pendientes = None
    profile = store.active(session)
    if profile is not None:
        prefs = Profile.model_validate(profile.perfil_json).preferences
        pendientes = len(pending_candidates(session, profile.id, profile.embedding, prefs))
        session.rollback()  # cierra la transacción que usó SET LOCAL
    return MatchStatus(last, sin_embedding or 0, pendientes)


def render(rows: list[SourceStats], match: MatchStatus | None = None) -> str:
    header = f"{'fuente':<28}{'activas':>9}{'nuevas24h':>11}{'en CR':>7}  última corrida (UTC)"
    lines = [header, "-" * len(header)]
    for r in rows:
        if r.ultima_corrida_ok is None:
            last = "nunca"
        else:
            last = f"{'ok' if r.ultima_corrida_ok else 'ERROR'} {r.ultima_corrida_en:%Y-%m-%d %H:%M}"
        name = r.key if r.activa else f"{r.key} (inactiva)"
        lines.append(f"{name:<28}{r.ofertas_activas:>9}{r.nuevas_24h:>11}{r.en_cr:>7}  {last}")
    lines.append("-" * len(header))
    lines.append(f"{'TOTAL':<28}{sum(r.ofertas_activas for r in rows):>9}"
                 f"{sum(r.nuevas_24h for r in rows):>11}{sum(r.en_cr for r in rows):>7}")
    zero = [r.key for r in rows if r.cero_en_dos_ultimas]
    if zero:
        lines.append("")
        lines.append("Fuentes con 0 ofertas en sus 2 últimas corridas: " + ", ".join(zero))
    if match is not None:
        lines.append("")
        if match.last is None:
            lines.append("Matching: nunca ha corrido")
        else:
            r = match.last
            lines.append(f"Matching {r.iniciado_en:%Y-%m-%d %H:%M} (UTC): candidatas={r.candidatas} "
                         f"evaluadas={r.evaluadas} fallidas={r.fallidas}"
                         + (" · cuota agotada" if r.cuota_agotada else ""))
        lines.append(f"Ofertas activas sin embedding: {match.sin_embedding}")
        if match.pendientes is not None:
            lines.append(f"Candidatas pendientes de evaluar: {match.pendientes}")
    return "\n".join(lines)
