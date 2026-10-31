from moneyplease.db.models import Application, JobLabel
from tests.api.conftest import NOW


def test_top_order_and_exclusions(client, world):
    prof = world.profile()
    a, b = world.job(titulo="A"), world.job(titulo="B")
    world.match(prof, a, 60)
    world.match(prof, b, 90)
    world.match(prof, world.job(titulo="NoAplica"), 99, fit="no_aplica")
    world.match(prof, world.job(titulo="Expirada", estado="expired"), 95)
    mala = world.job(titulo="Mala")
    world.match(prof, mala, 97)
    world.session.add(JobLabel(job_id=mala.id, etiqueta="mala"))
    world.session.commit()
    body = client.get("/api/top").json()
    assert [i["job"]["titulo"] for i in body] == ["B", "A"]
    assert body[0]["match"]["score"] == 90 and body[0]["match"]["fortalezas"] == ["Java"]


def test_top_without_profile_empty(client, world):
    world.job()
    assert client.get("/api/top").json() == []


def test_top_includes_label_and_application(client, world):
    prof = world.profile()
    j = world.job()
    world.match(prof, j)
    world.session.add(JobLabel(job_id=j.id, etiqueta="buena"))
    world.session.add(Application(job_id=j.id, estado="guardada", estado_desde=NOW, creado_en=NOW, actualizado_en=NOW))
    world.session.commit()
    item = client.get("/api/top").json()[0]
    assert item["etiqueta"] == "buena" and item["postulacion_id"] is not None


def test_feedback_upsert_and_clear(client, world):
    j = world.job()
    assert client.post(f"/api/jobs/{j.id}/feedback", json={"valor": "interesa"}).status_code == 204
    assert world.session.get(JobLabel, j.id).etiqueta == "buena"
    client.post(f"/api/jobs/{j.id}/feedback", json={"valor": "no_interesa"})
    world.session.expire_all()
    assert world.session.get(JobLabel, j.id).etiqueta == "mala"
    client.post(f"/api/jobs/{j.id}/feedback", json={"valor": None})
    world.session.expire_all()
    assert world.session.get(JobLabel, j.id) is None


def test_feedback_invalid_value_422(client, world):
    j = world.job()
    assert client.post(f"/api/jobs/{j.id}/feedback", json={"valor": "tal vez"}).status_code == 422


def test_feedback_unknown_job_404(client):
    assert client.post("/api/jobs/99999/feedback", json={"valor": "interesa"}).status_code == 404
