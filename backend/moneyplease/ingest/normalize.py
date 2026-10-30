import hashlib
import re
import unicodedata
from datetime import UTC

from bs4 import BeautifulSoup

from moneyplease.ingest.base import RawJob

PROVINCIAS = ["San José", "Alajuela", "Cartago", "Heredia", "Guanacaste", "Puntarenas", "Limón"]
CIUDADES = {
    "San José": ["Escazú", "Santa Ana", "Curridabat", "San Pedro", "Montes de Oca", "Tibás", "Moravia",
                 "Desamparados", "Pavas", "Rohrmoser", "La Sabana"],
    "Heredia": ["Belén", "San Pablo", "Santo Domingo", "Barreal", "Lagunilla", "Ultrapark"],
    "Alajuela": ["Coyol", "El Coyol", "Grecia"],
    "Cartago": ["Tres Ríos", "La Unión", "Paraíso"],
}
INEQUIVOCOS = {"Alajuela", "Heredia", "Guanacaste", "Puntarenas", "Escazú", "Curridabat", "Tibás",
               "Montes de Oca", "Rohrmoser", "Ultrapark", "Coyol", "El Coyol", "Tres Ríos", "Belén", "Lagunilla"}
HIBRIDO =["hybrid", "hibrido"]
REMOTO = ["remote", "remoto", "teletrabajo", "work from home"]
PRESENCIAL = ["on site", "onsite", "presencial", "in office"]
WORKPLACE = {"remote": "remoto", "hybrid": "hibrido", "onsite": "presencial", "on-site": "presencial"}


def canonical(text: str | None) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _has(text: str, words: list[str]) -> bool:
    return any(re.search(rf"\b{re.escape(canonical(w))}\b", text) for w in words)


def job_hash(company: str, title: str, location: str | None) -> str:
    key = f"{canonical(company)}|{canonical(title)}|{canonical(location)}"
    return hashlib.sha256(key.encode()).hexdigest()


def html_to_text(html: str) -> str:
    if not html:
        return ""
    text = BeautifulSoup(html, "html.parser").get_text("\n")
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def detect_modalidad(job: RawJob) -> str:
    if job.remote_hint is True:
        return "remoto"
    if job.workplace_hint and job.workplace_hint.lower() in WORKPLACE:
        return WORKPLACE[job.workplace_hint.lower()]
    text = canonical(" ".join([job.title, job.location or "", job.description]))
    if _has(text, HIBRIDO):
        return "hibrido"
    if _has(text, REMOTO):
        return "remoto"
    if _has(text, PRESENCIAL):
        return "presencial"
    return "desconocida"


def detect_ubicacion(text: str) -> tuple[str | None, str | None]:
    t = canonical(text)
    # Nombres como "San José", "Santa Ana" o "Grecia" existen fuera de CR: solo cuentan con contexto de CR.
    contexto_cr = _has(t, ["costa rica", "cr", *INEQUIVOCOS])
    for prov in PROVINCIAS:
        for name in [prov, *CIUDADES.get(prov, [])]:
            if _has(t, [name]) and (contexto_cr or name in INEQUIVOCOS):
                return prov, "CR"
    if _has(t, ["costa rica"]):
        return None, "CR"
    return None, None


def normalize(job: RawJob) -> dict:
    ubicacion = job.location or ""
    provincia, pais = detect_ubicacion(ubicacion)
    published = job.published_at
    if published is not None and published.tzinfo is None:
        published = published.replace(tzinfo=UTC)
    return {
        "external_id": job.external_id,
        "titulo": job.title,
        "empresa": job.company,
        "ubicacion": ubicacion,
        "modalidad": detect_modalidad(job),
        "provincia": provincia,
        "pais": pais,
        "descripcion": html_to_text(job.description),
        "url": job.url,
        "publicado_en": published,
        "hash": job_hash(job.company, job.title, ubicacion),
        "raw_json": job.raw,
    }
