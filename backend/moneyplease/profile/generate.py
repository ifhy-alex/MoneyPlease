from pydantic import ValidationError

from moneyplease.matching.llm import LLMError, LLMProvider
from moneyplease.profile.schema import DEFAULT_PREFERENCES, Profile

_STR = {"type": "STRING"}

PROFILE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "skills": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
            "name": _STR,
            "level": {"type": "STRING", "enum": ["basico", "intermedio", "avanzado"]},
            "evidence": _STR,
        }, "required": ["name", "level"]}},
        "languages": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
            "name": _STR, "level": _STR}, "required": ["name", "level"]}},
        "experience_months": {"type": "INTEGER"},
        "seniority_target": {"type": "ARRAY", "items": {"type": "STRING", "enum": ["practica", "junior"]}},
        "roles_target": {"type": "ARRAY", "items": _STR},
        "summary": _STR,
    },
    "required": ["skills", "languages", "experience_months", "seniority_target", "roles_target", "summary"],
}

SYSTEM_PROMPT = """Eres un asistente que convierte un CV en un perfil estructurado para buscar empleo.
Devuelve solo JSON con este contenido, en español:
- skills: tecnologías y habilidades técnicas concretas (máximo 60), cada una con level
  (basico, intermedio o avanzado según la evidencia del CV) y evidence (proyecto o puesto donde se usó).
- languages: idiomas con su nivel (por ejemplo B2, nativo).
- experience_months: meses de experiencia laboral profesional (no cuentan proyectos académicos).
- seniority_target: "practica" y/o "junior" según el nivel de la persona.
- roles_target: hasta 10 roles a los que podría aplicar (por ejemplo Backend Developer).
- summary: resumen profesional de máximo 600 caracteres, sin datos personales.
No inventes información que no esté en el CV."""


def draft_from_text(redacted: str, llm: LLMProvider) -> Profile:
    error: Exception | None = None
    for _ in range(2):
        try:
            data = llm.generate_json(SYSTEM_PROMPT, f"<cv>\n{redacted}\n</cv>", PROFILE_SCHEMA)
            return Profile.model_validate({**data, "preferences": DEFAULT_PREFERENCES.model_dump()})
        except (LLMError, ValidationError) as exc:
            error = exc
    raise LLMError(f"el LLM no devolvió un perfil válido: {error}")
