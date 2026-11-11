from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from moneyplease.api.deps import get_session
from moneyplease.api.schemas import DuplicateRef, JobOut, MatchOut, TopItem
from moneyplease.db.models import Application, Job, JobLabel, Match, Source
from moneyplease.duplicates import duplicates_of
from moneyplease.profile import store
from moneyplease.scope import Ambito, where_scope

router = APIRouter()
DUPLICATE_SLACK = 10  # filas extra para seguir devolviendo n después de agrupar


@router.get("/top", response_model=list[TopItem])
def top(n: int = Query(10, ge=1, le=50), ambito: Ambito | None = None,
        session: Session = Depends(get_session)) -> list[TopItem]:
    active = store.active(session)
    if active is None:
        return []
    query = (
        select(Match, Job, Source.key, JobLabel.etiqueta, Application.id)
        .join(Job, Job.id == Match.job_id)
        .join(Source, Source.id == Job.source_id)
        .outerjoin(JobLabel, JobLabel.job_id == Job.id)
        .outerjoin(Application, Application.job_id == Job.id)
        .where(Match.profile_id == active.id, Job.estado == "active", Match.fit != "no_aplica",
               or_(JobLabel.etiqueta.is_(None), JobLabel.etiqueta != "mala"))
        .order_by(Match.score.desc(), Match.evaluado_en.desc())
        .limit(min(n, 50) + DUPLICATE_SLACK)
    )
    scope = where_scope(ambito)
    rows = session.execute(query if scope is None else query.where(scope)).all()
    # Las publicaciones casi idénticas se muestran como una sola tarjeta: la de mayor puntaje (va primero).
    items, hidden = [], set()
    for match, job, key, label, app_id in rows:
        if job.id in hidden:
            continue
        dups = duplicates_of(session, job)
        hidden.update(d.id for d in dups)
        items.append(TopItem(job=JobOut.of(job, key), match=MatchOut.of(match), etiqueta=label,
                             postulacion_id=app_id, duplicados=DuplicateRef.of_all(dups)))
        if len(items) == n:
            break
    return items
