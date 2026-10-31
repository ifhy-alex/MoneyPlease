"""Ofertas que el usuario marcó como interesantes o no, usadas como ejemplos de preferencia para el LLM."""
import hashlib
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from moneyplease.db.models import Job, JobLabel, Match

MIN_LABELS = 6
MIN_EACH = 2
MAX_EACH = 4


@dataclass(frozen=True)
class Ejemplo:
    titulo: str
    empresa: str
    resumen: str
    le_intereso: bool
    job_id: int | None = None


def select_examples(session: Session, profile_id: int) -> tuple[list[Ejemplo], str | None]:
    rows = session.execute(
        select(JobLabel.job_id, JobLabel.etiqueta, Job.titulo, Job.empresa, Match.resumen)
        .join(Job, Job.id == JobLabel.job_id)
        .join(Match, (Match.job_id == JobLabel.job_id) & (Match.profile_id == profile_id))
        .order_by(JobLabel.creado_en.desc(), JobLabel.job_id.desc())
    ).all()
    buenas = [r for r in rows if r.etiqueta == "buena"]
    malas = [r for r in rows if r.etiqueta == "mala"]
    if len(rows) < MIN_LABELS or len(buenas) < MIN_EACH or len(malas) < MIN_EACH:
        return [], None
    chosen = buenas[:MAX_EACH] + malas[:MAX_EACH]
    ejemplos = [Ejemplo(r.titulo, r.empresa, (r.resumen or "")[:120], r.etiqueta == "buena", r.job_id)
                for r in chosen]
    key = ",".join(str(i) for i in sorted(r.job_id for r in chosen))
    return ejemplos, hashlib.sha256(key.encode()).hexdigest()[:16]
