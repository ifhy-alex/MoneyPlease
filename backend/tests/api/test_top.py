import pytest

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


@pytest.mark.parametrize("n", [-1, 0, 51])
def test_n_fuera_de_rango_es_422(client, n):
    assert client.get(f"/api/top?n={n}").status_code == 422


def test_brechas_vacias_guardadas_antes_no_se_muestran(client, world):
    prof = world.profile()
    job = world.job()
    world.match(prof, job, brechas=["Ninguna brecha técnica significativa para una pasantía", "Docker"])
    item = client.get("/api/top").json()[0]
    assert item["match"]["brechas"] == ["Docker"]


def _hpe_pair(world, prof):
    from tests.api.test_map import near
    a = world.job(empresa="HPE", url="https://hpe/1216552", embedding=near(prof.embedding, 0.9, 1))
    b = world.job(empresa="HPE", url="https://hpe/1214221", embedding=list(a.embedding))
    return a, b


def test_top_agrupa_duplicados_y_mantiene_n(client, world):
    from tests.api.test_map import near
    prof = world.profile()
    a, b = _hpe_pair(world, prof)
    world.match(prof, a, score=95)
    world.match(prof, b, score=94)
    for i in range(10):
        world.match(prof, world.job(empresa=f"E{i}", embedding=near(prof.embedding, 0.8, 50 + i)), score=80 - i)
    items = client.get("/api/top?n=10").json()
    ids = [i["job"]["id"] for i in items]
    assert len(items) == 10 and a.id in ids and b.id not in ids
    first = next(i for i in items if i["job"]["id"] == a.id)
    assert first["duplicados"] == [{"job_id": b.id, "url": "https://hpe/1214221"}]


def test_explorar_marca_sin_ocultar(client, world):
    prof = world.profile()
    a, b = _hpe_pair(world, prof)
    items = {i["job"]["id"]: i for i in client.get("/api/jobs").json()["items"]}
    assert items[a.id]["duplicados"] == [{"job_id": b.id, "url": b.url}]
    assert items[b.id]["duplicados"] == [{"job_id": a.id, "url": a.url}]


def test_detalle_lista_duplicados(client, world):
    prof = world.profile()
    a, b = _hpe_pair(world, prof)
    assert client.get(f"/api/jobs/{a.id}").json()["duplicados"] == [{"job_id": b.id, "url": b.url}]


def test_feedback_aplica_al_grupo(client, world, session):
    from moneyplease.db.models import JobLabel
    prof = world.profile()
    a, b = _hpe_pair(world, prof)
    assert client.post(f"/api/jobs/{a.id}/feedback", json={"valor": "no_interesa"}).status_code == 204
    session.expire_all()
    assert {session.get(JobLabel, a.id).etiqueta, session.get(JobLabel, b.id).etiqueta} == {"mala"}
    assert client.post(f"/api/jobs/{b.id}/feedback", json={"valor": None}).status_code == 204
    session.expire_all()
    assert session.get(JobLabel, a.id) is None and session.get(JobLabel, b.id) is None


def test_top_marca_las_evaluadas_solo_con_titulo(client, world):
    prof = world.profile()
    world.match(prof, world.job(titulo="Intern", descripcion=""), score=65)
    world.match(prof, world.job(titulo="Backend", descripcion="Java y Spring"), score=60)
    flags = {i["job"]["titulo"]: i["job"]["solo_titulo"] for i in client.get("/api/top").json()}
    assert flags == {"Intern": True, "Backend": False}
