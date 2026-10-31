from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from moneyplease.api.deps import get_session
from moneyplease.db.models import Job, JobLabel

router = APIRouter()
LABELS = {"interesa": "buena", "no_interesa": "mala"}


class Feedback(BaseModel):
    valor: Literal["interesa", "no_interesa"] | None


@router.post("/jobs/{job_id}/feedback", status_code=204)
def feedback(job_id: int, body: Feedback, session: Session = Depends(get_session)) -> Response:
    if session.get(Job, job_id) is None:
        raise HTTPException(404, "La oferta no existe")
    existing = session.get(JobLabel, job_id)
    if body.valor is None:
        if existing:
            session.delete(existing)
    elif existing:
        existing.etiqueta = LABELS[body.valor]
    else:
        session.add(JobLabel(job_id=job_id, etiqueta=LABELS[body.valor]))
    session.commit()
    return Response(status_code=204)
