import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from moneyplease.api.deps import get_session
from moneyplease.api.schemas import MapData, MapPoint
from moneyplease.db.models import Job, JobLabel, Match
from moneyplease.matching.filters import passes
from moneyplease.profile import store
from moneyplease.profile.schema import Profile
from moneyplease.projection import project

router = APIRouter()
MAX_POINTS = 300
CANDIDATES = 600  # margen para los que quitan los filtros duros


@router.get("/map", response_model=MapData)
def get_map(session: Session = Depends(get_session)) -> MapData:
    active = store.active(session)
    if active is None:
        raise HTTPException(404, "Todavía no hay perfil guardado")
    prefs = Profile.model_validate(active.perfil_json).preferences
    rows = session.execute(
        select(Job, Match.score, JobLabel.etiqueta)
        .outerjoin(Match, and_(Match.job_id == Job.id, Match.profile_id == active.id))
        .outerjoin(JobLabel, JobLabel.job_id == Job.id)
        .where(Job.estado == "active", Job.embedding.is_not(None),
               or_(JobLabel.etiqueta.is_(None), JobLabel.etiqueta != "mala"))
        .order_by(Job.embedding.cosine_distance(active.embedding))
        .limit(CANDIDATES)).all()
    rows = [r for r in rows if passes(r[0], prefs)][:MAX_POINTS]
    profile_vec = np.asarray(active.embedding, dtype=float)
    jobs = np.asarray([r[0].embedding for r in rows], dtype=float).reshape(len(rows), len(profile_vec))
    coords = project(profile_vec, jobs, [r[0].id for r in rows])
    puntos = [MapPoint(job_id=job.id, titulo=job.titulo, empresa=job.empresa, x=x, y=y, similitud=s,
                       puntaje=score, etiqueta=etiqueta)
              for (job, score, etiqueta), (x, y, s) in zip(rows, coords)]
    return MapData(total=len(puntos), puntos=puntos)
