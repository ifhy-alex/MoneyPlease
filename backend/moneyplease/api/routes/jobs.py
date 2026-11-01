from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from moneyplease.api.deps import get_session
from moneyplease.api.schemas import JobOut, MatchOut
from moneyplease.db.models import Application, Job, JobLabel, Match, Source
from moneyplease.ingest.normalize import html_to_text
from moneyplease.insights import CR
from moneyplease.profile import store

router = APIRouter()
LABELS = {"interesa": "buena", "no_interesa": "mala"}


class Feedback(BaseModel):
    valor: Literal["interesa", "no_interesa"] | None


@router.post("/jobs/{job_id}/feedback", status_code=204)
def feedback(job_id: int, body: Feedback, session: Session = Depends(get_session)) -> Response:
    if session.get(Job, job_id) is None:
        raise HTTPException(404, "La oferta no existe")
    if body.valor is None:
        session.execute(delete(JobLabel).where(JobLabel.job_id == job_id))
    else:
        # Upsert: dos clics seguidos sobre la misma oferta no chocan con la clave única.
        etiqueta = LABELS[body.valor]
        session.execute(insert(JobLabel).values(job_id=job_id, etiqueta=etiqueta)
                        .on_conflict_do_update(index_elements=[JobLabel.job_id], set_={"etiqueta": etiqueta}))
    session.commit()
    return Response(status_code=204)


PAGE_SIZE = 25


class ExploreItem(BaseModel):
    job: JobOut
    match: MatchOut | None
    etiqueta: str | None


class ExplorePage(BaseModel):
    items: list[ExploreItem]
    total: int
    page: int


def _like(q: str) -> str:
    escaped = q.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
    return f"%{escaped}%"


@router.get("/jobs", response_model=ExplorePage)
def explore(q: str | None = None, source: str | None = None, modalidad: str | None = None,
            solo_cr: bool = False, min_score: int | None = None, fit: str | None = None,
            desde: date | None = None, page: int = Query(1, ge=1), sort: Literal["score", "fecha"] = "score",
            session: Session = Depends(get_session)) -> ExplorePage:
    active = store.active(session)
    match_join = and_(Match.job_id == Job.id, Match.profile_id == (active.id if active else -1))
    query = (select(Job, Source.key, Match, JobLabel.etiqueta)
             .join(Source, Source.id == Job.source_id)
             .outerjoin(Match, match_join)
             .outerjoin(JobLabel, JobLabel.job_id == Job.id)
             .where(Job.estado == "active"))
    if q and q.strip():
        pattern = func.unaccent(func.lower(_like(q.strip())))
        query = query.where(or_(*(func.unaccent(func.lower(col)).like(pattern, escape="\\")
                                  for col in (Job.titulo, Job.empresa, Job.descripcion))))
    if source:
        query = query.where(Source.key.startswith(f"{source}:") | (Source.key == source))
    if modalidad:
        query = query.where(Job.modalidad == modalidad)
    if solo_cr:
        query = query.where(Job.pais == "CR")
    if min_score is not None:
        query = query.where(Match.score >= min_score)
    if fit:
        query = query.where(Match.fit == fit)
    if desde:
        query = query.where(Job.primera_vez_visto >= datetime.combine(desde, datetime.min.time(), CR))
    total = session.scalar(select(func.count()).select_from(query.subquery()))
    order = ([Job.primera_vez_visto.desc()] if sort == "fecha"
             else [Match.score.desc().nulls_last(), Job.primera_vez_visto.desc()])
    rows = session.execute(query.order_by(*order, Job.id.desc())
                           .offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)).all()
    return ExplorePage(items=[ExploreItem(job=JobOut.of(job, key), match=MatchOut.of(match), etiqueta=label)
                              for job, key, match, label in rows], total=total or 0, page=page)


class PostulacionRef(BaseModel):
    id: int
    estado: str


class JobDetail(BaseModel):
    job: JobOut
    descripcion_texto: str
    match: MatchOut | None
    etiqueta: str | None
    postulacion: PostulacionRef | None


@router.get("/jobs/{job_id}", response_model=JobDetail)
def detail(job_id: int, session: Session = Depends(get_session)) -> JobDetail:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "La oferta no existe")
    active = store.active(session)
    match = session.get(Match, (active.id, job_id)) if active else None
    label = session.get(JobLabel, job_id)
    application = session.scalar(select(Application).where(Application.job_id == job_id))
    return JobDetail(job=JobOut.of(job, session.get(Source, job.source_id).key),
                     descripcion_texto=html_to_text(job.descripcion or ""),
                     match=MatchOut.of(match), etiqueta=label.etiqueta if label else None,
                     postulacion=PostulacionRef(id=application.id, estado=application.estado) if application else None)
