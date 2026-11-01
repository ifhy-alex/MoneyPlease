"""Asignación de skills a áreas (backend, frontend, datos…) para el arte y las agregaciones del dashboard."""
import re
import unicodedata

from moneyplease.ingest.normalize import canonical

AREAS = ("backend", "frontend", "datos", "cloud", "testing", "idiomas")

_BY_AREA = {
    "backend": ["c#", "c++", "java", "spring", "spring boot", "spring cloud", "python", "django", "flask", "fastapi", "node",
                "node.js", "express", ".net", "go", "golang", "php", "laravel", "ruby", "rails", "kotlin",
                "rest", "restful apis", "graphql", "microservices", "microservicios", "api", "apis", "hibernate",
                "jpa", "kafka", "rabbitmq"],
    "frontend": ["react", "react native", "angular", "vue", "svelte", "next.js", "javascript", "typescript",
                 "html", "css", "tailwind", "tailwind css", "sass", "redux", "react router", "react hook form",
                 "ios", "swift", "android", "flutter", "figma", "ux", "ui"],
    "datos": ["sql", "mysql", "postgresql", "postgres", "sql server", "oracle", "mongodb", "nosql", "snowflake",
              "power bi", "tableau", "excel", "etl", "data warehouse", "azure data warehouse", "olap", "spark",
              "pandas", "airflow", "dbt", "bigquery", "machine learning", "estadistica", "data analysis"],
    "cloud": ["docker", "kubernetes", "aws", "azure", "gcp", "google cloud", "terraform", "ci/cd", "github ci",
              "github actions", "jenkins", "linux", "devops", "azure cli", "aws kiro", "microservices architecture",
              "redes", "networking", "seguridad", "security"],
    "testing": ["junit", "mockito", "pytest", "selenium", "cypress", "jest", "testing", "pruebas",
                "unit testing", "qa", "automation", "automatizacion"],
    "idiomas": ["ingles", "english", "espanol", "spanish", "frances", "portugues", "aleman"],
}

# Nombres de una sola letra (por ejemplo "c#" → "c") coincidirían con cualquier letra suelta: se descartan.
SKILL_AREA: dict[str, str] = {canonical(skill): area for area, skills in _BY_AREA.items() for skill in skills
                              if len(canonical(skill)) >= 2}
# Las más largas primero, para que "spring boot" gane sobre "spring".
_BY_LENGTH = sorted((k for k in SKILL_AREA if k), key=len, reverse=True)


def find_skill(text: str) -> str | None:
    """La skill conocida más larga que aparece como palabra completa en el texto (forma canónica)."""
    t = canonical(text)
    if not t:
        return None
    for skill in _BY_LENGTH:
        if re.search(rf"\b{re.escape(skill)}\b", t):
            return skill
    return None


def fold_skill(text: str) -> str:
    """Minúsculas y sin acentos, pero conservando # + . / (canonical los borra: "C#" quedaría "c")."""
    text = unicodedata.normalize("NFKD", (text or "").lower())
    return re.sub(r"\s+", " ", "".join(c for c in text if not unicodedata.combining(c))).strip()


FOLDED_AREA: dict[str, str] = {fold_skill(skill): area for area, skills in _BY_AREA.items() for skill in skills}
_FOLDED_BY_LENGTH = sorted(FOLDED_AREA, key=len, reverse=True)


def skills_in(text: str) -> set[str]:
    """Todas las skills conocidas que aparecen como palabra completa; la más larga gana si se solapan."""
    t = fold_skill(text)
    found: set[str] = set()
    for skill in _FOLDED_BY_LENGTH:
        pattern = rf"(?<![\w#+.]){re.escape(skill)}(?![\w#+])"
        if re.search(pattern, t):
            found.add(skill)
            t = re.sub(pattern, " ", t)  # "spring boot" no cuenta además como "spring"
    return found


def area_of(skill: str) -> str:
    if fold_skill(skill) in FOLDED_AREA:
        return FOLDED_AREA[fold_skill(skill)]
    key = canonical(skill)
    if key in SKILL_AREA:
        return SKILL_AREA[key]
    found = find_skill(skill)
    return SKILL_AREA[found] if found else "otros"
