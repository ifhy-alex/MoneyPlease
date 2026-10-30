import html
from datetime import UTC, datetime

from moneyplease.ingest.base import ConnectorResult, RawJob
from moneyplease.ingest.http import PoliteClient


class GreenhouseConnector:
    is_complete_listing = True

    def __init__(self, slug: str, company: str, client: PoliteClient):
        self.slug = slug
        self.company = company
        self.client = client
        self.key = f"greenhouse:{slug}"

    def fetch(self) -> ConnectorResult:
        # API JSON pública pensada para integraciones; su robots.txt aplica al sitio web.
        resp = self.client.get(f"https://boards-api.greenhouse.io/v1/boards/{self.slug}/jobs",
                               params={"content": "true"}, check_robots=False)
        jobs = []
        for j in resp.json().get("jobs", []):
            updated = j.get("updated_at")
            jobs.append(RawJob(
                external_id=str(j["id"]),
                title=j["title"],
                company=self.company,
                location=(j.get("location") or {}).get("name"),
                description=html.unescape(j.get("content") or ""),
                url=j["absolute_url"],
                published_at=datetime.fromisoformat(updated).astimezone(UTC) if updated else None,
                raw=j,
            ))
        return ConnectorResult(jobs)
