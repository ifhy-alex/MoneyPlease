from dataclasses import dataclass, field

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from moneyplease.db.models import Job, JobLabel, Match

ETIQUETAS = ("buena", "regular", "mala")


def top_matches(session: Session, profile_id: int, n: int, fit: str | None = None,
                min_score: int | None = None, hide_rejected: bool = False) -> list[tuple[Match, Job]]:
    query = (select(Match, Job).join(Job, Job.id == Match.job_id)
             .where(Match.profile_id == profile_id, Job.estado == "active"))
    if hide_rejected:  # lo mismo que muestra /api/top: sin las marcadas "no me interesa"
        query = query.outerjoin(JobLabel, JobLabel.job_id == Job.id).where(
            or_(JobLabel.etiqueta.is_(None), JobLabel.etiqueta != "mala"))
    query = query.where(Match.fit == fit) if fit else query.where(Match.fit != "no_aplica")
    if min_score is not None:
        query = query.where(Match.score >= min_score)
    return list(session.execute(query.order_by(Match.score.desc(), Match.evaluado_en.desc()).limit(n)).all())


def render_top(rows: list[tuple[Match, Job]]) -> str:
    if not rows:
        return "Sin resultados todavía: corre `match` o revisa los filtros del perfil."
    blocks = []
    for match, job in rows:
        lines = [f"[{job.id}] {match.score} · {match.fit} · {job.titulo} — {job.empresa}",
                 f"    {job.ubicacion or 'sin ubicación'} ({job.modalidad})"]
        lines += [f"    + {f}" for f in match.fortalezas]
        lines += [f"    - {b}" for b in match.brechas]
        lines += [f"    {match.resumen}", f"    {job.url}"]
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def label(session: Session, job_id: int, etiqueta: str) -> None:
    if etiqueta not in ETIQUETAS:
        raise ValueError(f"etiqueta inválida: {etiqueta}")
    if session.get(Job, job_id) is None:
        raise ValueError(f"no existe la oferta {job_id}")
    existing = session.get(JobLabel, job_id)
    if existing:
        existing.etiqueta = etiqueta
    else:
        session.add(JobLabel(job_id=job_id, etiqueta=etiqueta))
    session.commit()


@dataclass
class EvalSummary:
    top10_etiquetadas: int
    top10_relevantes: int
    score_promedio: dict[str, float] = field(default_factory=dict)


def summary(session: Session, profile_id: int) -> EvalSummary:
    top_ids = [job.id for _, job in top_matches(session, profile_id, 10)]
    labels = dict(session.execute(select(JobLabel.job_id, JobLabel.etiqueta)).all())
    in_top = [labels[i] for i in top_ids if i in labels]
    scored = session.execute(select(JobLabel.etiqueta, Match.score)
                             .join(Match, Match.job_id == JobLabel.job_id)
                             .where(Match.profile_id == profile_id)).all()
    promedio = {}
    for etiqueta in ETIQUETAS:
        scores = [s for e, s in scored if e == etiqueta]
        if scores:
            promedio[etiqueta] = sum(scores) / len(scores)
    return EvalSummary(len(in_top), sum(1 for e in in_top if e in ("buena", "regular")), promedio)


def render_summary(s: EvalSummary) -> str:
    lines = [f"Top 10: {s.top10_etiquetadas} etiquetadas",
             f"Punto de control: {s.top10_relevantes}/10 relevantes (meta ≥ 5)"]
    for etiqueta, avg in s.score_promedio.items():
        lines.append(f"Score promedio de las '{etiqueta}': {avg:.1f}")
    return "\n".join(lines)
