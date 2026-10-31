from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from moneyplease import eval as ev
from moneyplease import insights
from moneyplease.api.deps import get_session, get_settings
from moneyplease.api.routes.applications import needs_followup, to_out
from moneyplease.config import Settings
from moneyplease.db.models import Application, IngestRun, Source
from moneyplease.profile import store
from moneyplease.profile.schema import Profile
from moneyplease.stats import match_status

router = APIRouter()


def _sources_with_error(session: Session) -> list[str]:
    out = []
    for source in session.scalars(select(Source).where(Source.activa).order_by(Source.key)):
        last = session.scalars(select(IngestRun).where(IngestRun.source_id == source.id)
                               .order_by(IngestRun.iniciado_en.desc()).limit(1)).first()
        if last is not None and not last.ok:
            out.append(source.key)
    return out


@router.get("/insights")
def overview(session: Session = Depends(get_session), settings: Settings = Depends(get_settings)) -> dict:
    now = datetime.now(UTC)
    active = store.active(session)
    status = match_status(session)
    last = status.last
    summary = ev.summary(session, active.id) if active else None
    apps = session.scalars(select(Application).where(Application.estado == "aplicada")).all()
    return {
        "demo": settings.demo_mode,
        "brechas_semana": [{"skill": s, "n": n} for s, n in insights.gaps_week(session, active.id, now)]
        if active else [],
        "estado": {
            "ultima_ingesta": session.scalar(select(func.max(IngestRun.terminado_en))),
            "fuentes_con_error": _sources_with_error(session),
            "matching": None if last is None else {
                "fecha": last.iniciado_en, "candidatas": last.candidatas, "evaluadas": last.evaluadas,
                "fallidas": last.fallidas, "cuota_agotada": last.cuota_agotada},
            "pendientes": status.pendientes,
        },
        "punto_control": {"relevantes": summary.top10_relevantes if summary else 0,
                          "etiquetadas": summary.top10_etiquetadas if summary else 0},
        "seguimiento": [to_out(session, a, settings, now) for a in apps
                        if needs_followup(a, now, settings.followup_days)],
    }


@router.get("/insights/skills")
def skills(session: Session = Depends(get_session)) -> list[dict]:
    active = store.active(session)
    if active is None:
        return []
    return insights.skills(session, Profile.model_validate(active.perfil_json), active.id)


@router.get("/insights/daily")
def daily(dias: int = Query(30, ge=1, le=365), session: Session = Depends(get_session)) -> list[dict]:
    active = store.active(session)
    return insights.daily(session, active.id if active else None, datetime.now(UTC), dias)


@router.get("/insights/flow")
def flow(semanas: int = Query(12, ge=1, le=104), session: Session = Depends(get_session)) -> list[dict]:
    return insights.flow(session, datetime.now(UTC), semanas)
