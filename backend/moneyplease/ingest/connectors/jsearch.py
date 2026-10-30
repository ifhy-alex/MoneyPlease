from datetime import UTC, date, datetime

import httpx

from moneyplease.ingest.base import ConnectorResult, QuotaExhausted, RawJob
from moneyplease.ingest.http import PoliteClient

HOST = "jsearch.p.rapidapi.com"
DEFAULT_QUERIES = [
    "developer Costa Rica",
    "practicante Costa Rica",
    "desarrollador junior Costa Rica",
    "software engineer Costa Rica",
    "data analyst Costa Rica",
]


def _next_month(today: date) -> date:
    return date(today.year + 1, 1, 1) if today.month == 12 else date(today.year, today.month + 1, 1)


def _published_at(j: dict) -> datetime | None:
    if ts := j.get("job_posted_at_timestamp"):
        return datetime.fromtimestamp(ts, UTC)
    if iso := j.get("job_posted_at_datetime_utc"):
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(UTC)
    return None


class JSearchConnector:
    key = "jsearch"
    is_complete_listing = False

    def __init__(self, api_key: str, config: dict, client: PoliteClient, today: date):
        self.api_key = api_key
        self.config = config
        self.client = client
        self.today = today

    def fetch(self) -> ConnectorResult:
        queries = self.config.get("queries") or DEFAULT_QUERIES
        index = self.config.get("query_index", 0)
        # v5 devuelve unas 10 ofertas por página; "month" rinde más que "week" con una sola request diaria.
        params = {"query": queries[index % len(queries)], "num_pages": 1, "country": "cr", "date_posted": "month"}
        headers = {"X-RapidAPI-Key": self.api_key, "X-RapidAPI-Host": HOST}
        try:
            resp = self.client.get(f"https://{HOST}/search-v2", params=params, headers=headers, check_robots=False)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                raise QuotaExhausted(_next_month(self.today)) from exc
            raise
        jobs = []
        for j in (resp.json().get("data") or {}).get("jobs", []):
            location = ", ".join(p for p in (j.get("job_city"), j.get("job_state"), j.get("job_country")) if p)
            jobs.append(RawJob(
                external_id=j["job_id"],
                title=j["job_title"],
                company=j.get("employer_name") or "",
                location=location or None,
                description=j.get("job_description") or "",
                url=j.get("job_apply_link") or "",
                published_at=_published_at(j),
                raw=j,
                remote_hint=j.get("job_is_remote"),
            ))
        return ConnectorResult(jobs, {"query_index": index + 1})
