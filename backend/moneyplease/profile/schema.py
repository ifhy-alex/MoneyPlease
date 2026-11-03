from typing import Literal

from pydantic import BaseModel, Field, field_validator

from moneyplease.ingest.normalize import PROVINCIAS


class Skill(BaseModel):
    name: str
    level: Literal["basico", "intermedio", "avanzado"]
    evidence: str | None = None


class Language(BaseModel):
    name: str
    level: str


class Preferences(BaseModel):
    modalidad: list[Literal["presencial", "hibrido", "remoto"]]
    ubicaciones: list[str]
    remoto_abierto: bool = True
    excluir_titulo: list[str]
    excluir_palabras: list[str]
    # Provincias donde se evalúan las ofertas de CR que no dicen su modalidad (las alertas de correo casi nunca
    # la traen). Si hay alguna, también entran las de CR sin provincia reconocida. Vacía: se descartan.
    desconocida_en: list[str] = []

    @field_validator("ubicaciones", "desconocida_en")
    @classmethod
    def _provincias(cls, value: list[str]) -> list[str]:
        unknown = [v for v in value if v not in PROVINCIAS]
        if unknown:
            raise ValueError(f"provincias desconocidas: {unknown}; válidas: {PROVINCIAS}")
        return value


class Profile(BaseModel):
    skills: list[Skill] = Field(max_length=60)
    languages: list[Language] = Field(max_length=10)
    experience_months: int = Field(ge=0)
    seniority_target: list[Literal["practica", "junior"]] = Field(min_length=1)
    roles_target: list[str] = Field(max_length=10)
    summary: str = Field(max_length=600)
    preferences: Preferences

    def llm_view(self) -> dict:
        """Lo único del perfil que se envía al LLM: nunca preferencias ni datos de contacto."""
        return self.model_dump(include={"skills", "languages", "experience_months", "roles_target",
                                        "seniority_target", "summary"})

    def embedding_text(self) -> str:
        return (f"query: {', '.join(self.roles_target)}. {self.summary} "
                f"Skills: {', '.join(s.name for s in self.skills)}")


DEFAULT_PREFERENCES = Preferences(
    modalidad=["presencial", "hibrido", "remoto"],
    ubicaciones=["Cartago", "San José", "Heredia", "Alajuela"],
    remoto_abierto=True,
    excluir_titulo=["senior", "sr", "lead", "staff", "principal", "manager", "director", "head", "architect"],
    excluir_palabras=["5+ years", "7+ years", "10+ years", "5 años", "más de 5 años"],
)
