import copy
import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
import respx

from moneyplease.config import Settings
from moneyplease.db.models import Job, Source
from moneyplease.ingest.base import SourceGone
from moneyplease.ingest.connectors import build_connector
from moneyplease.ingest.connectors.himalayas import LOCATION, QUERIES, HimalayasConnector
from moneyplease.ingest.http import PoliteClient
from moneyplease.ingest.normalize import normalize
from moneyplease.matching.filters import passes
from moneyplease.profile.schema import DEFAULT_PREFERENCES

FIX = json.loads((Path(__file__).parent / "fixtures/himalayas_search.json").read_text(encoding="utf-8"))
URL = "https://himalayas.app/jobs/api/search"
EMPTY = {"totalCount": 0, "jobs": []}


def connector():
    return HimalayasConnector(PoliteClient(sleep=lambda s: None))


def route(q, page, body):
    # El cliente revisa robots.txt antes de la API: el de Himalayas solo prohíbe páginas del sitio, no /jobs/api.
    respx.get("https://himalayas.app/robots.txt").respond(200, text="User-Agent: *\nDisallow: /apply\n")
    return respx.get(URL, params={"q": q, "country": "CR", "page": str(page)}).respond(200, json=body)


@respx.mock
def test_himalayas_keeps_only_internships_open_to_costa_rica():
    first = route(QUERIES[0], 1, FIX)
    for q in QUERIES[1:]:
        route(q, 1, EMPTY)
    c = connector()
    assert c.key == "himalayas" and c.is_complete_listing
    jobs = c.fetch().jobs
    assert first.called
    # "Junior Project Manager" no es pasantía: queda fuera.
    assert [j.title for j in jobs] == ["Application Developer Intern", "Trainee Flutter Developer"]
    j = jobs[0]
    assert j.company == "Orion Labs"
    assert j.external_id == j.url == "https://himalayas.app/companies/orion-labs/jobs/application-developer-intern"
    assert j.location == LOCATION
    assert j.remote_hint is True
    assert j.published_at == datetime.fromtimestamp(1793538716, UTC)
    assert "Python and React" in j.description


@respx.mock
def test_himalayas_dedupes_across_queries_and_pages():
    page1 = copy.deepcopy(FIX)
    page1["totalCount"] = 4
    page2 = {"totalCount": 4, "jobs": [{**FIX["jobs"][0], "title": "Data Engineer Intern",
                                        "guid": "https://himalayas.app/companies/orion-labs/jobs/data-engineer-intern"}]}
    route(QUERIES[0], 1, page1)
    route(QUERIES[0], 2, page2)
    route(QUERIES[1], 1, FIX)  # las mismas ofertas otra vez
    for q in QUERIES[2:]:
        route(q, 1, EMPTY)
    titles = [j.title for j in connector().fetch().jobs]
    assert titles == ["Application Developer Intern", "Trainee Flutter Developer", "Data Engineer Intern"]


@respx.mock
def test_himalayas_respects_robots():
    respx.get("https://himalayas.app/robots.txt").respond(200, text="User-Agent: *\nDisallow: /jobs/api\n")
    with pytest.raises(SourceGone):
        connector().fetch()


@respx.mock
def test_himalayas_internship_passes_profile_filters():
    route(QUERIES[0], 1, FIX)
    for q in QUERIES[1:]:
        route(q, 1, EMPTY)
    row = normalize(connector().fetch().jobs[0])
    assert row["modalidad"] == "remoto"
    job = Job(**{k: row[k] for k in ("titulo", "empresa", "ubicacion", "modalidad", "provincia", "pais",
                                     "descripcion")})
    assert passes(job, DEFAULT_PREFERENCES)


def test_build_connector_himalayas():
    src = Source(key="himalayas", nombre="Himalayas", tipo="api", config_json={})
    assert isinstance(build_connector(src, Settings(_env_file=None), PoliteClient(), date.today()), HimalayasConnector)


@respx.mock
def test_himalayas_unescapes_html_entities():
    body = {"totalCount": 1, "jobs": [{**FIX["jobs"][0], "title": "R&amp;D Intern", "companyName": "H&amp;H Group"}]}
    route(QUERIES[0], 1, body)
    for q in QUERIES[1:]:
        route(q, 1, EMPTY)
    j = connector().fetch().jobs[0]
    assert (j.title, j.company) == ("R&D Intern", "H&H Group")
