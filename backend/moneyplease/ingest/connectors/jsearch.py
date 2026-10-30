from datetime import UTC, date, datetime

import httpx

from moneyplease.ingest.base import ConnectorResult, QuotaExhausted, RawJob
from moneyplease.ingest.http import PoliteClient

HOST = "jsearch.p.rapidapi.com"
DEFAULT_QUERIES = [
    "practica profesional informatica Costa Rica",
    "junior developer Costa Rica",
    "intern software developer remote",
]


def _next_month(today: date) -> date:
    return date(today.year + 1, 1, 1) if today.month == 12 else date(today.year, today.month + 1, 1)


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
        params = {"query": queries[index % len(queries)], "page": 1, "num_pages": 1,
                  "country": "cr", "date_posted": "week"}
        headers = {"X-RapidAPI-Key": self.api_key, "X-RapidAPI-Host": HOST}
        try:
            resp = self.client.get(f"https://{HOST}/search", params=params, headers=headers, check_robots=False)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                raise QuotaExhausted(_next_month(self.today)) from exc
            raise
        jobs = []
        for j in resp.json().get("data", []):
            ts = j.get("job_posted_at_timestamp")
            location = ", ".join(p for p in (j.get("job_city"), j.get("job_state"), j.get("job_country")) if p)
            jobs.append(RawJob(
                external_id=j["job_id"],
                title=j["job_title"],
                company=j.get("employer_name") or "",
                location=location or None,
                description=j.get("job_description") or "",
                url=j.get("job_apply_link") or "",
                published_at=datetime.fromtimestamp(ts, UTC) if ts else None,
                raw=j,
                remote_hint=j.get("job_is_remote"),
            ))
        return ConnectorResult(jobs, {"query_index": index + 1})
