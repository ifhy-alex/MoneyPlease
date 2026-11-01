import copy
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
import respx

from moneyplease.ingest.base import SourceGone
from moneyplease.ingest.connectors.workday import WorkdayConnector
from moneyplease.ingest.http import PoliteClient

# Respuestas reales de TransUnion (recortadas): facets, listado filtrado por CR y detalle de 3 ofertas.
FIX = Path(__file__).parent / "fixtures/workday"
FACETS = json.loads((FIX / "facets.json").read_text(encoding="utf-8"))
LISTING = json.loads((FIX / "listing.json").read_text(encoding="utf-8"))
DETAILS = [json.loads((FIX / f"detail_{i}.json").read_text(encoding="utf-8")) for i in range(3)]
HOST = "https://transunion.wd5.myworkdayjobs.com"
API = f"{HOST}/wday/cxs/transunion/TransUnion"
ROBOTS_OK = "User-agent: *\nDisallow: /refreshFacet/\n"


def connector():
    return WorkdayConnector("transunion", "wd5", "TransUnion", "TransUnion", PoliteClient(sleep=lambda s: None))


def mock_site(listings, details=DETAILS, robots=ROBOTS_OK, facets=FACETS):
    respx.get(f"{HOST}/robots.txt").respond(200, text=robots)
    jobs = respx.post(f"{API}/jobs").mock(
        side_effect=[httpx.Response(200, json=facets)] + [httpx.Response(200, json=page) for page in listings])
    for posting, detail in zip(sum((p["jobPostings"] for p in listings), []), details * 100):
        respx.get(f"{API}{posting['externalPath']}").respond(200, json=detail)
    return jobs


def cr_id():
    loc = next(f for f in FACETS["facets"] if f["facetParameter"] == "locationMainGroup")
    sub = next(v for v in loc["values"] if "values" in v)
    return next(v["id"] for v in sub["values"] if v["descriptor"] == "Costa Rica")


@respx.mock
def test_parses_real_fixture():
    jobs_route = mock_site([LISTING])
    c = connector()
    assert c.key == "workday:transunion" and c.is_complete_listing
    jobs = c.fetch().jobs
    assert len(jobs) == 3
    info = DETAILS[0]["jobPostingInfo"]
    j = jobs[0]
    assert j.external_id == info["jobReqId"]
    assert j.title == info["title"] and j.company == "TransUnion"
    assert j.location == f"{info['location']}, Costa Rica"
    assert j.url == info["externalUrl"]
    assert j.published_at == datetime.fromisoformat(info["startDate"]).replace(tzinfo=UTC)
    assert j.description == info["jobDescription"]
    body = json.loads(jobs_route.calls[1].request.content)
    assert body["appliedFacets"] == {"locationCountry": [cr_id()]}


@respx.mock
def test_no_costa_rica_returns_empty():
    facets = copy.deepcopy(FACETS)

    def drop_cr(values):
        kept = []
        for v in values:
            if "values" in v:
                v["values"] = drop_cr(v["values"])
            if "costa rica" not in str(v.get("descriptor", "")).lower():
                kept.append(v)
        return kept

    for f in facets["facets"]:
        f["values"] = drop_cr(f.get("values", []))
    jobs_route = mock_site([], facets=facets)
    assert connector().fetch().jobs == []
    assert jobs_route.call_count == 1


@respx.mock
def test_paginates():
    template = LISTING["jobPostings"][0]
    postings = [{**template, "externalPath": f"/job/x/J{i}"} for i in range(25)]
    pages = [{"total": 25, "jobPostings": postings[:20]}, {"total": 25, "jobPostings": postings[20:]}]
    jobs_route = mock_site(pages, details=[DETAILS[0]])
    assert len(connector().fetch().jobs) == 25
    offsets = [json.loads(call.request.content)["offset"] for call in jobs_route.calls[1:]]
    assert offsets == [0, 20]


@respx.mock
def test_remote_type_hint():
    detail = copy.deepcopy(DETAILS[0])
    detail["jobPostingInfo"]["remoteType"] = "Hybrid"
    mock_site([{"total": 1, "jobPostings": LISTING["jobPostings"][:1]}], details=[detail])
    assert connector().fetch().jobs[0].workplace_hint == "hybrid"


@respx.mock
def test_robots_disallow_site_is_source_gone():
    mock_site([LISTING], robots="User-agent: *\nDisallow: /TransUnion/\n")
    with pytest.raises(SourceGone):
        connector().fetch()


@respx.mock
def test_404_is_source_gone():
    respx.get(f"{HOST}/robots.txt").respond(200, text=ROBOTS_OK)
    respx.post(f"{API}/jobs").respond(404)
    with pytest.raises(SourceGone):
        connector().fetch()


MAINTENANCE = "https://community.workday.com/maintenance-page"


@respx.mock
def test_redireccion_a_mantenimiento():
    from moneyplease.ingest.base import Maintenance
    respx.get(f"{HOST}/robots.txt").respond(200, text=ROBOTS_OK)
    respx.post(f"{API}/jobs").respond(303, headers={"Location": MAINTENANCE})
    respx.get(MAINTENANCE).respond(200, html="<html>maintenance</html>")
    with pytest.raises(Maintenance, match="Workday en mantenimiento"):
        connector().fetch()


@respx.mock
def test_detalle_en_mantenimiento():
    from moneyplease.ingest.base import Maintenance
    respx.get(f"{HOST}/robots.txt").respond(200, text=ROBOTS_OK)
    respx.post(f"{API}/jobs").mock(side_effect=[httpx.Response(200, json=FACETS), httpx.Response(200, json=LISTING)])
    respx.get(url__startswith=f"{API}/job").respond(303, headers={"Location": MAINTENANCE})
    respx.get(MAINTENANCE).respond(200, html="<html>maintenance</html>")
    with pytest.raises(Maintenance, match="Workday en mantenimiento"):
        connector().fetch()
