from datetime import date, datetime

from pydantic import BaseModel

from moneyplease.db.models import Job, Match
from moneyplease.matching.score import drop_empty_gaps


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
        # Los matches guardados antes del filtro de "ninguna brecha" también se limpian al leer.
        return cls(score=match.score, fit=match.fit, fortalezas=match.fortalezas,
                   brechas=drop_empty_gaps(match.brechas), resumen=match.resumen)


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


class MapPoint(BaseModel):
    job_id: int
    titulo: str
    empresa: str
    x: float
    y: float
    similitud: float
    puntaje: int | None
    etiqueta: str | None


class MapData(BaseModel):
    total: int
    puntos: list[MapPoint]


class GraphSkill(BaseModel):
    nombre: str
    nivel: str | None
    area: str
    grado: int
    tiene: bool


class GraphOffer(BaseModel):
    job_id: int
    titulo: str
    empresa: str
    puntaje: int


class GraphEdge(BaseModel):
    habilidad: str
    job_id: int


class SkillsGraph(BaseModel):
    habilidades: list[GraphSkill]
    ofertas: list[GraphOffer]
    aristas: list[GraphEdge]
