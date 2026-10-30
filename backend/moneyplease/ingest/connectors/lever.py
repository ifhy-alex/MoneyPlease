from datetime import UTC, datetime

from moneyplease.ingest.base import ConnectorResult, RawJob
from moneyplease.ingest.http import PoliteClient


def _description(j: dict) -> str:
    parts = [j.get("descriptionPlain") or ""]
    for item in j.get("lists") or []:
        parts.append(item.get("text") or "")
        parts.append(item.get("content") or "")
    parts.append(j.get("additionalPlain") or "")
    return "\n".join(p for p in parts if p)


class LeverConnector:
    is_complete_listing = True

    def __init__(self, slug: str, company: str, client: PoliteClient):
        self.slug = slug
        self.company = company
        self.client = client
        self.key = f"lever:{slug}"

    def fetch(self) -> ConnectorResult:
        # API JSON pública pensada para integraciones; su robots.txt aplica al sitio web.
        resp = self.client.get(f"https://api.lever.co/v0/postings/{self.slug}",
                               params={"mode": "json"}, check_robots=False)
        jobs = []
        for j in resp.json():
            created = j.get("createdAt")
            jobs.append(RawJob(
                external_id=j["id"],
                title=j["text"],
                company=self.company,
                location=(j.get("categories") or {}).get("location"),
                description=_description(j),
                url=j["hostedUrl"],
                published_at=datetime.fromtimestamp(created / 1000, UTC) if created else None,
                raw=j,
                workplace_hint=j.get("workplaceType"),
            ))
        return ConnectorResult(jobs)
