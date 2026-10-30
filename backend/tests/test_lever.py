import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import respx

from moneyplease.ingest.base import SourceGone
from moneyplease.ingest.connectors.lever import LeverConnector
from moneyplease.ingest.http import PoliteClient

FIX = json.loads((Path(__file__).parent / "fixtures/lever_postings.json").read_text(encoding="utf-8"))
URL = "https://api.lever.co/v0/postings/toptal"


def connector():
    return LeverConnector("toptal", "Toptal", PoliteClient(sleep=lambda s: None))


@respx.mock
def test_lever_parses_jobs():
    respx.get(URL).respond(200, json=FIX)
    c = connector()
    assert c.key == "lever:toptal" and c.is_complete_listing
    jobs = c.fetch().jobs
    assert len(jobs) == 3
    j, f = jobs[0], FIX[0]
    assert j.external_id == f["id"]
    assert j.title == f["text"]
    assert j.published_at == datetime.fromtimestamp(f["createdAt"] / 1000, UTC)
    assert j.workplace_hint == f["workplaceType"]
    assert j.url == f["hostedUrl"]
    assert f["descriptionPlain"][:40] in j.description


@respx.mock
def test_lever_404_source_gone():
    respx.get(URL).respond(404)
    with pytest.raises(SourceGone):
        connector().fetch()
