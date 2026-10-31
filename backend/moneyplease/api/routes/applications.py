from datetime import UTC, date, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from moneyplease.api.deps import get_session, get_settings
from moneyplease.api.schemas import ApplicationOut, JobOut, MatchOut
from moneyplease.config import Settings
from moneyplease.db.models import Application, Job, Match, Source
from moneyplease.insights import CR
from moneyplease.profile import store

router = APIRouter()
Estado = Literal["guardada", "aplicada", "entrevista", "oferta", "rechazada"]


def needs_followup(app: Application, now: datetime, days: int) -> bool:
    if app.estado != "aplicada" or app.estado_desde > now - timedelta(days=days):
        return False
    return app.recordatorio_hasta is None or app.recordatorio_hasta <= now


def to_out(session: Session, app: Application, settings: Settings, now: datetime) -> ApplicationOut:
    job = session.get(Job, app.job_id)
    active = store.active(session)
    match = session.get(Match, (active.id, job.id)) if active else None
    return ApplicationOut(
        id=app.id, estado=app.estado, notas=app.notas, fecha_aplicacion=app.fecha_aplicacion,
        siguiente_paso=app.siguiente_paso, estado_desde=app.estado_desde, recordatorio_hasta=app.recordatorio_hasta,
        seguimiento=needs_followup(app, now, settings.followup_days),
        dias_en_estado=(now - app.estado_desde).days,
        job=JobOut.of(job, session.get(Source, job.source_id).key), match=MatchOut.of(match))


class NewApplication(BaseModel):
    job_id: int
    estado: Estado = "guardada"


class ApplicationPatch(BaseModel):
    estado: Estado | None = None
    notas: str | None = None
    fecha_aplicacion: date | None = None
    siguiente_paso: str | None = None
    recordatorio_hasta: datetime | None = None


def _get(session: Session, app_id: int) -> Application:
    app = session.get(Application, app_id)
    if app is None:
        raise HTTPException(404, "La postulación no existe")
    return app


@router.get("/applications", response_model=list[ApplicationOut])
def list_applications(session: Session = Depends(get_session),
                      settings: Settings = Depends(get_settings)) -> list[ApplicationOut]:
    now = datetime.now(UTC)
    apps = session.scalars(select(Application).order_by(Application.actualizado_en.desc())).all()
    return [to_out(session, a, settings, now) for a in apps]


@router.post("/applications", response_model=ApplicationOut, status_code=201)
def create_application(body: NewApplication, session: Session = Depends(get_session),
                       settings: Settings = Depends(get_settings)) -> ApplicationOut:
    if session.get(Job, body.job_id) is None:
        raise HTTPException(404, "La oferta no existe")
    now = datetime.now(UTC)
    app = Application(job_id=body.job_id, estado=body.estado, notas="", siguiente_paso="", estado_desde=now,
                      creado_en=now, actualizado_en=now)
    session.add(app)
    try:
        session.commit()
    except IntegrityError:  # ya existe (doble clic o dos pestañas)
        session.rollback()
        raise HTTPException(409, "Esa oferta ya está en postulaciones")
    return to_out(session, app, settings, now)


@router.patch("/applications/{app_id}", response_model=ApplicationOut)
def update_application(app_id: int, body: ApplicationPatch, session: Session = Depends(get_session),
                       settings: Settings = Depends(get_settings)) -> ApplicationOut:
    app = _get(session, app_id)
    now = datetime.now(UTC)
    changes = body.model_dump(exclude_unset=True)
    for field in ("notas", "siguiente_paso"):
        if field in changes:
            setattr(app, field, changes[field] or "")
    for field in ("fecha_aplicacion", "recordatorio_hasta"):
        if field in changes:
            setattr(app, field, changes[field])
    if body.estado and body.estado != app.estado:
        app.estado, app.estado_desde = body.estado, now
        if body.estado == "aplicada" and app.fecha_aplicacion is None:
            app.fecha_aplicacion = now.astimezone(CR).date()
    app.actualizado_en = now
    session.commit()
    return to_out(session, app, settings, now)


@router.delete("/applications/{app_id}", status_code=204)
def delete_application(app_id: int, session: Session = Depends(get_session)) -> Response:
    session.delete(_get(session, app_id))
    session.commit()
    return Response(status_code=204)
