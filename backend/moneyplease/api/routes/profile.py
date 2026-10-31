from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from moneyplease.api.deps import get_embedder, get_llm, get_session, get_settings
from moneyplease.config import Settings
from moneyplease.db.models import Profile as ProfileRow
from moneyplease.matching.llm import LLMError, QuotaExceeded
from moneyplease.profile import store
from moneyplease.profile.extract import redact
from moneyplease.profile.generate import draft_from_text
from moneyplease.profile.schema import Profile
from moneyplease.skill_areas import AREAS, area_of

router = APIRouter()
LEVELS = {"basico": 1, "intermedio": 2, "avanzado": 3}
MAX_PDF = 5 * 1024 * 1024


class ProfileVersion(BaseModel):
    version: int
    creado_en: datetime
    perfil: Profile
    areas: dict[str, int]


class Draft(BaseModel):
    perfil: Profile
    texto_enviado: str


def _areas(perfil: Profile) -> dict[str, int]:
    totals = dict.fromkeys(AREAS, 0)
    for skill in perfil.skills:
        area = area_of(skill.name)
        if area in totals:
            totals[area] += LEVELS[skill.level]
    return totals


def _version(row: ProfileRow) -> ProfileVersion:
    perfil = Profile.model_validate(row.perfil_json)
    return ProfileVersion(version=row.version, creado_en=row.creado_en, perfil=perfil, areas=_areas(perfil))


@router.get("/profile", response_model=ProfileVersion)
def get_profile(session: Session = Depends(get_session)) -> ProfileVersion:
    row = store.active(session)
    if row is None:
        raise HTTPException(404, "Todavía no hay perfil guardado")
    return _version(row)


@router.put("/profile", response_model=ProfileVersion, status_code=201)
def put_profile(perfil: Profile, session: Session = Depends(get_session),
                embedder=Depends(get_embedder)) -> ProfileVersion:
    cv_text = (store.active(session).cv_texto if store.active(session) else "")
    for attempt in range(2):
        try:
            return _version(store.save(session, perfil, cv_text, embedder))
        except IntegrityError:  # dos guardados simultáneos tomaron la misma versión: reintentar
            session.rollback()
            if attempt:
                raise
    raise AssertionError("unreachable")


@router.get("/profile/versions", response_model=list[ProfileVersion])
def versions(session: Session = Depends(get_session)) -> list[ProfileVersion]:
    rows = session.scalars(select(ProfileRow).order_by(ProfileRow.version.desc())).all()
    return [_version(r) for r in rows]


@router.post("/profile/from-cv", response_model=Draft)
async def from_cv(archivo: UploadFile = File(...), settings: Settings = Depends(get_settings),
                  llm=Depends(get_llm)) -> Draft:
    if settings.demo_mode:
        raise HTTPException(503, "Modo demo: generar el perfil desde un CV está desactivado")
    if llm is None:
        raise HTTPException(503, "Falta GEMINI_API_KEY en .env")
    data = await archivo.read(MAX_PDF + 1)
    if archivo.content_type != "application/pdf" or not data.startswith(b"%PDF"):
        raise HTTPException(422, "El archivo debe ser un PDF")
    if len(data) > MAX_PDF:
        raise HTTPException(422, "El PDF supera los 5 MB")
    private = settings.private_dir
    private.mkdir(parents=True, exist_ok=True)
    (private / "cv.pdf").write_bytes(data)
    redacted = redact(store.pdf_text(private / "cv.pdf"))
    (private / "cv.txt").write_text(redacted, encoding="utf-8")
    try:
        perfil = draft_from_text(redacted, llm)
    except QuotaExceeded:
        raise HTTPException(429, "Gemini respondió que se agotó la cuota gratuita; intenta más tarde")
    except (LLMError, httpx.HTTPError) as exc:
        raise HTTPException(502, f"Gemini no devolvió un perfil utilizable: {type(exc).__name__}")
    return Draft(perfil=perfil, texto_enviado=redacted)
