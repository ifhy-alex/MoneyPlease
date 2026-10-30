import json
from datetime import UTC
from pathlib import Path

import pytest
import respx

from moneyplease.ingest.base import SourceGone
from moneyplease.ingest.connectors.greenhouse import GreenhouseConnector
from moneyplease.ingest.http import PoliteClient

FIX = json.loads((Path(__file__).parent / "fixtures/greenhouse_jobs.json").read_text(encoding="utf-8"))
URL = "https://boards-api.greenhouse.io/v1/boards/konradgroup/jobs"


def connector():
    return GreenhouseConnector("konradgroup", "Konrad Group", PoliteClient(sleep=lambda s: None))


@respx.mock
def test_greenhouse_parses_jobs():
    respx.get(URL).respond(200, json=FIX)
    c = connector()
    assert c.key == "greenhouse:konradgroup" and c.is_complete_listing
    jobs = c.fetch().jobs
    assert len(jobs) == 3
    j = jobs[0]
    assert j.external_id == str(FIX["jobs"][0]["id"])
    assert j.company == "Konrad Group"
    assert j.location == "Costa Rica"
    assert j.url.startswith("https://")
    assert j.published_at.tzinfo == UTC
    assert "&lt;" not in j.description and "<p>" in j.description


@respx.mock
def test_greenhouse_404_source_gone():
    respx.get(URL).respond(404)
    with pytest.raises(SourceGone):
        connector().fetch()
