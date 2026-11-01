import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, or_, select, text
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


def visible_jobs(session: Session, active) -> list[tuple[Job, int | None, str | None, str | None]]:
    """Ofertas que se dibujan en el mapa y el universo: (oferta, puntaje, etiqueta, fit), las más parecidas primero."""
    prefs = Profile.model_validate(active.perfil_json).preferences
    # Igual que la preselección del matching: sin el índice HNSW (con filtros devuelve muy pocas filas) y con
    # un filtro de lugar barato en SQL, para que las ofertas extranjeras parecidas no llenen la ventana.
    session.execute(text("SET LOCAL enable_indexscan = off"))
    place = or_(Job.pais == "CR", Job.modalidad == "remoto") if prefs.remoto_abierto else Job.pais == "CR"
    rows = session.execute(
        select(Job, Match.score, JobLabel.etiqueta, Match.fit)
        .outerjoin(Match, and_(Match.job_id == Job.id, Match.profile_id == active.id))
        .outerjoin(JobLabel, JobLabel.job_id == Job.id)
        .where(Job.estado == "active", Job.embedding.is_not(None), place,
               or_(JobLabel.etiqueta.is_(None), JobLabel.etiqueta != "mala"))
        .order_by(Job.embedding.cosine_distance(active.embedding))
        .limit(CANDIDATES)).all()
    return [tuple(r) for r in rows if passes(r[0], prefs)][:MAX_POINTS]


def embeddings(active, rows) -> tuple[np.ndarray, np.ndarray]:
    profile_vec = np.asarray(active.embedding, dtype=float)
    jobs = np.asarray([r[0].embedding for r in rows], dtype=float).reshape(len(rows), len(profile_vec))
    return profile_vec, jobs


@router.get("/map", response_model=MapData)
def get_map(session: Session = Depends(get_session)) -> MapData:
    active = store.active(session)
    if active is None:
        raise HTTPException(404, "Todavía no hay perfil guardado")
    rows = visible_jobs(session, active)
    profile_vec, jobs = embeddings(active, rows)
    coords = project(profile_vec, jobs, [r[0].id for r in rows])
    puntos = [MapPoint(job_id=job.id, titulo=job.titulo, empresa=job.empresa, x=x, y=y, similitud=s,
                       puntaje=score, etiqueta=etiqueta)
              for (job, score, etiqueta, _), (x, y, s) in zip(rows, coords)]
    return MapData(total=len(puntos), puntos=puntos)
