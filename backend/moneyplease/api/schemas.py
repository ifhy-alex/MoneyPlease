from datetime import date, datetime

from pydantic import BaseModel

from moneyplease.db.models import Job, Match


class JobOut(BaseModel):
    id: int
    titulo: str
    empresa: str
    ubicacion: str
    modalidad: str
    pais: str | None
    url: str
    fuente: str
    publicado_en: datetime | None
    primera_vez_visto: datetime

    @classmethod
    def of(cls, job: Job, fuente: str) -> "JobOut":
        return cls(id=job.id, titulo=job.titulo, empresa=job.empresa, ubicacion=job.ubicacion,
                   modalidad=job.modalidad, pais=job.pais, url=job.url, fuente=fuente,
                   publicado_en=job.publicado_en, primera_vez_visto=job.primera_vez_visto)


class MatchOut(BaseModel):
    score: int
    fit: str
    fortalezas: list[str]
    brechas: list[str]
    resumen: str

    @classmethod
    def of(cls, match: Match | None) -> "MatchOut | None":
        if match is None:
            return None
        return cls(score=match.score, fit=match.fit, fortalezas=match.fortalezas, brechas=match.brechas,
                   resumen=match.resumen)


class TopItem(BaseModel):
    job: JobOut
    match: MatchOut
    etiqueta: str | None
    postulacion_id: int | None


class ApplicationOut(BaseModel):
    id: int
    estado: str
    notas: str
    fecha_aplicacion: date | None
    siguiente_paso: str
    estado_desde: datetime
    recordatorio_hasta: datetime | None
    seguimiento: bool
    dias_en_estado: int
    job: JobOut
    match: MatchOut | None
