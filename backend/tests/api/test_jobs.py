from datetime import timedelta

import pytest

from tests.api.conftest import NOW


@pytest.fixture
def jobs(world):
    prof = world.profile()
    a = world.job(titulo="Backend José", empresa="Acme", modalidad="remoto", pais=None, provincia=None,
                  descripcion="Java y Spring")
    b = world.job(titulo="Data Analyst", empresa="O'Reilly", modalidad="hibrido",
                  descripcion="SQL 100% remoto_parcial", primera_vez_visto=NOW - timedelta(days=10))
    c = world.job(titulo="QA", empresa="Beta", modalidad="presencial")
    world.match(prof, a, 90, fit="junior")
    world.match(prof, b, 60, fit="practica")
    return a, b, c


def titles(resp):
    return [i["job"]["titulo"] for i in resp.json()["items"]]


def test_default_lists_active_sorted_by_score(client, jobs):
    body = client.get("/api/jobs").json()
    assert body["total"] == 3 and body["page"] == 1
    assert [i["job"]["titulo"] for i in body["items"]][:2] == ["Backend José", "Data Analyst"]
    assert body["items"][2]["match"] is None


def test_filters(client, jobs):
    assert titles(client.get("/api/jobs", params={"modalidad": "remoto"})) == ["Backend José"]
    assert set(titles(client.get("/api/jobs", params={"solo_cr": True}))) == {"Data Analyst", "QA"}
    assert titles(client.get("/api/jobs", params={"min_score": 70})) == ["Backend José"]
    assert titles(client.get("/api/jobs", params={"fit": "practica"})) == ["Data Analyst"]
    assert titles(client.get("/api/jobs", params={"source": "greenhouse"}))
    desde = (NOW - timedelta(days=2)).date().isoformat()
    assert "Data Analyst" not in titles(client.get("/api/jobs", params={"desde": desde}))


def test_search_accents_case(client, jobs):
    assert titles(client.get("/api/jobs", params={"q": "josé"})) == ["Backend José"]
    assert titles(client.get("/api/jobs", params={"q": "JOSE"})) == ["Backend José"]
    assert titles(client.get("/api/jobs", params={"q": "spring"})) == ["Backend José"]


def test_search_special_chars(client, jobs):
    assert titles(client.get("/api/jobs", params={"q": "%"})) == ["Data Analyst"]
    assert titles(client.get("/api/jobs", params={"q": "_"})) == ["Data Analyst"]
    assert titles(client.get("/api/jobs", params={"q": "O'Reilly"})) == ["Data Analyst"]
    assert client.get("/api/jobs", params={"q": "   "}).json()["total"] == 3


def test_sort_by_date(client, jobs):
    assert titles(client.get("/api/jobs", params={"sort": "fecha"}))[-1] == "Data Analyst"


def test_pagination_25(client, world):
    for _ in range(30):
        world.job()
    body = client.get("/api/jobs", params={"page": 2}).json()
    assert body["total"] == 30 and len(body["items"]) == 5


def test_detail_text_not_html(client, world):
    j = world.job(descripcion="<p>Hola</p><script>alert(1)</script><ul><li>Java</li></ul>")
    body = client.get(f"/api/jobs/{j.id}").json()
    assert "<" not in body["descripcion_texto"] and "Hola" in body["descripcion_texto"]
    assert body["match"] is None and body["postulacion"] is None


def test_detail_404(client):
    assert client.get("/api/jobs/99999").status_code == 404


def test_feedback_upsert_no_falla_si_la_etiqueta_aparece_entre_medias(client, world, session, monkeypatch):
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from moneyplease.db.models import JobLabel
    job = world.job()
    session.add(JobLabel(job_id=job.id, etiqueta="buena"))
    session.commit()
    original = Session.get
    # Como en la carrera real: la otra petición insertó la etiqueta después de que esta la buscara.
    monkeypatch.setattr(Session, "get", lambda self, model, *a, **k:
                        None if model is JobLabel else original(self, model, *a, **k))
    resp = client.post(f"/api/jobs/{job.id}/feedback", json={"valor": "no_interesa"})
    assert resp.status_code == 204
    session.expire_all()
    rows = session.scalars(select(JobLabel).where(JobLabel.job_id == job.id)).all()
    assert [r.etiqueta for r in rows] == ["mala"]
