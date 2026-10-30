import copy
import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
import respx

from moneyplease.ingest.base import QuotaExhausted
from moneyplease.ingest.connectors.jsearch import JSearchConnector
from moneyplease.ingest.http import PoliteClient

# Respuesta real de JSearch v5 (/search-v2), recortada a 3 ofertas.
FIX = json.loads((Path(__file__).parent / "fixtures/jsearch_search.json").read_text(encoding="utf-8"))
URL = "https://jsearch.p.rapidapi.com/search-v2"
QUERIES = ["q0", "q1", "q2"]


def connector(index=0, today=date(2026, 10, 30)):
    return JSearchConnector("KEY", {"queries": QUERIES, "query_index": index},
                            PoliteClient(sleep=lambda s: None), today)


@respx.mock
def test_rotates_query():
    route = respx.get(URL).respond(200, json=FIX)
    c = connector(index=4)
    assert c.key == "jsearch" and not c.is_complete_listing
    result = c.fetch()
    req = route.calls[0].request
    assert req.url.params["query"] == "q1"
    assert req.url.params["country"] == "cr"
    assert req.url.params["num_pages"] == "1"
    assert req.headers["X-RapidAPI-Key"] == "KEY"
    assert result.config_updates == {"query_index": 5}


@respx.mock
def test_parses_v5_results():
    respx.get(URL).respond(200, json=FIX)
    jobs = connector().fetch().jobs
    first = FIX["data"]["jobs"][0]
    assert len(jobs) == 3
    assert jobs[0].external_id == first["job_id"]
    assert jobs[0].title == "Lead Software Engineer"
    assert jobs[0].company == "HCLTech"
    assert jobs[0].location == "Heredia, Heredia, CR"
    assert jobs[0].remote_hint is False
    assert jobs[0].published_at is None
    assert jobs[0].url == first["job_apply_link"]


@respx.mock
def test_published_at_fallbacks():
    body = copy.deepcopy(FIX)
    body["data"]["jobs"][0]["job_posted_at_timestamp"] = 1792000000
    body["data"]["jobs"][1]["job_posted_at_datetime_utc"] = "2026-10-29T15:00:00.000Z"
    respx.get(URL).respond(200, json=body)
    jobs = connector().fetch().jobs
    assert jobs[0].published_at == datetime.fromtimestamp(1792000000, UTC)
    assert jobs[1].published_at == datetime(2026, 10, 29, 15, tzinfo=UTC)


@respx.mock
def test_location_skips_empty_parts():
    body = copy.deepcopy(FIX)
    body["data"]["jobs"][0]["job_state"] = None
    respx.get(URL).respond(200, json=body)
    assert connector().fetch().jobs[0].location == "Heredia, CR"


@respx.mock
def test_empty_results():
    respx.get(URL).respond(200, json={"status": "OK", "data": {"jobs": [], "cursor": None}})
    result = connector().fetch()
    assert result.jobs == [] and result.config_updates == {"query_index": 1}


@respx.mock
def test_429_quota_until_next_month():
    respx.get(URL).respond(429)
    with pytest.raises(QuotaExhausted) as exc:
        connector(today=date(2026, 12, 15)).fetch()
    assert exc.value.until == date(2027, 1, 1)
