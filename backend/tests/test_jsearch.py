import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
import respx

from moneyplease.ingest.base import QuotaExhausted
from moneyplease.ingest.connectors.jsearch import JSearchConnector
from moneyplease.ingest.http import PoliteClient

FIX = json.loads((Path(__file__).parent / "fixtures/jsearch_search.json").read_text(encoding="utf-8"))
URL = "https://jsearch.p.rapidapi.com/search"
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
    assert req.headers["X-RapidAPI-Key"] == "KEY"
    assert result.config_updates == {"query_index": 5}


@respx.mock
def test_parses_results():
    respx.get(URL).respond(200, json=FIX)
    jobs = connector().fetch().jobs
    assert [j.external_id for j in jobs] == ["abc123==", "def456=="]
    assert jobs[0].company == "Empresa Ficticia S.A."
    assert jobs[0].location == "Heredia, Heredia Province, CR"
    assert jobs[1].location == "San José, CR"
    assert jobs[1].remote_hint is True
    assert jobs[0].published_at == datetime.fromtimestamp(1792000000, UTC)


@respx.mock
def test_429_quota_until_next_month():
    respx.get(URL).respond(429)
    with pytest.raises(QuotaExhausted) as exc:
        connector(today=date(2026, 12, 15)).fetch()
    assert exc.value.until == date(2027, 1, 1)
