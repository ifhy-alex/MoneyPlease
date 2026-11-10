"""Pasantías remotas abiertas a Costa Rica, desde la API pública de búsqueda de Himalayas."""
import html
import re
from datetime import UTC, datetime

from moneyplease.ingest.base import ConnectorResult, RawJob
from moneyplease.ingest.http import PoliteClient

URL = "https://himalayas.app/jobs/api/search"
QUERIES = ["intern", "internship", "trainee"]
# El filtro country=CR de la API ya deja solo las ofertas que aceptan candidatos en Costa Rica.
LOCATION = "Remoto · abierto a Costa Rica"
INTERNSHIP = re.compile(r"\b(intern|internship|trainee|apprentice|apprenticeship|pr[aá]ctica|pasant[ií]a)\b", re.I)
MAX_PAGES = 5  # 20 ofertas por página; hoy cada búsqueda cabe en una


def is_internship(j: dict) -> bool:
    return bool(INTERNSHIP.search(j.get("title") or "")) or j.get("employmentType") == "Intern"


class HimalayasConnector:
    key = "himalayas"
    # Cada corrida trae todas las pasantías vigentes: las que desaparecen de Himalayas expiran solas.
    is_complete_listing = True

    def __init__(self, client: PoliteClient):
        self.client = client

    def _search(self, query: str) -> list[dict]:
        found: list[dict] = []
        for page in range(1, MAX_PAGES + 1):
            data = self.client.get(URL, params={"q": query, "country": "CR", "page": page}).json()
            found += data.get("jobs") or []
            if not data.get("jobs") or len(found) >= (data.get("totalCount") or 0):
                break
        return found

    def fetch(self) -> ConnectorResult:
        jobs: dict[str, RawJob] = {}
        for query in QUERIES:
            for j in self._search(query):
                guid = j.get("guid")
                if not guid or guid in jobs or not is_internship(j):
                    continue
                pub = j.get("pubDate")
                # El enlace va a la página de la oferta en Himalayas, como piden sus términos de uso.
                jobs[guid] = RawJob(
                    external_id=guid,
                    title=html.unescape(j["title"]),  # la API manda algunos nombres con entidades ("H&amp;H")
                    company=html.unescape(j.get("companyName") or ""),
                    location=LOCATION,
                    description=j.get("description") or j.get("excerpt") or "",
                    url=guid,
                    published_at=datetime.fromtimestamp(pub, UTC) if pub else None,
                    raw=j,
                    remote_hint=True,
                )
        return ConnectorResult(list(jobs.values()))
