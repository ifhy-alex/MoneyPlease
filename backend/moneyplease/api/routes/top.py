from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from moneyplease.api.deps import get_session
from moneyplease.api.schemas import JobOut, MatchOut, TopItem
from moneyplease.db.models import Application, Job, JobLabel, Match, Source
from moneyplease.profile import store

router = APIRouter()


@router.get("/top", response_model=list[TopItem])
def top(n: int = 10, session: Session = Depends(get_session)) -> list[TopItem]:
    active = store.active(session)
    if active is None:
        return []
    rows = session.execute(
        select(Match, Job, Source.key, JobLabel.etiqueta, Application.id)
        .join(Job, Job.id == Match.job_id)
        .join(Source, Source.id == Job.source_id)
        .outerjoin(JobLabel, JobLabel.job_id == Job.id)
        .outerjoin(Application, Application.job_id == Job.id)
        .where(Match.profile_id == active.id, Job.estado == "active", Match.fit != "no_aplica",
               or_(JobLabel.etiqueta.is_(None), JobLabel.etiqueta != "mala"))
        .order_by(Match.score.desc(), Match.evaluado_en.desc())
        .limit(min(n, 50))
    ).all()
    return [TopItem(job=JobOut.of(job, key), match=MatchOut.of(match), etiqueta=label, postulacion_id=app_id)
            for match, job, key, label, app_id in rows]
