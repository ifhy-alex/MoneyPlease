from datetime import UTC, datetime, timedelta

from moneyplease.db.models import Application, IngestRun, JobLabel, MatchRun, Source


def test_insights_without_profile(client):
    body = client.get("/api/insights").json()
    assert body["demo"] is False
    assert body["brechas_semana"] == [] and body["seguimiento"] == []
    assert body["punto_control"] == {"relevantes": 0, "etiquetadas": 0}
    assert body["estado"]["matching"] is None and body["estado"]["pendientes"] is None


def test_insights_shape_with_data(client, world):
    prof = world.profile()
    now = datetime.now(UTC)
    j = world.job()
    world.match(prof, j, 80, brechas=["Pide Kubernetes"], evaluado_en=now)
    world.session.add(JobLabel(job_id=j.id, etiqueta="buena"))
    world.session.add(MatchRun(profile_id=prof.id, iniciado_en=now, terminado_en=now, candidatas=3, evaluadas=2,
                               fallidas=0, cuota_agotada=False))
    world.session.add(Application(job_id=j.id, estado="aplicada", estado_desde=now - timedelta(days=11),
                                  creado_en=now, actualizado_en=now))
    world.session.commit()
    body = client.get("/api/insights").json()
    assert body["brechas_semana"] == [{"skill": "kubernetes", "n": 1}]
    assert body["punto_control"] == {"relevantes": 1, "etiquetadas": 1}
    assert body["estado"]["matching"]["evaluadas"] == 2
    assert [a["job"]["id"] for a in body["seguimiento"]] == [j.id]


def test_fuentes_con_error(client, world):
    other = Source(key="lever:y", nombre="Y", tipo="ats", config_json={})
    world.session.add(other)
    world.session.flush()
    now = datetime.now(UTC)
    world.session.add(IngestRun(source_id=world.source.id, iniciado_en=now - timedelta(hours=1), terminado_en=now,
                                ok=True, ofertas_traidas=1, ofertas_nuevas=0))
    world.session.add(IngestRun(source_id=other.id, iniciado_en=now, terminado_en=now, ok=False, error="x",
                                ofertas_traidas=0, ofertas_nuevas=0))
    world.session.commit()
    estado = client.get("/api/insights").json()["estado"]
    assert estado["fuentes_con_error"] == ["lever:y"]
    assert estado["ultima_ingesta"] is not None


def test_skills_daily_flow_endpoints(client, world):
    prof = world.profile()
    world.match(prof, world.job(), fortalezas=["Spring Boot"])
    assert any(s["skill"] == "spring boot" for s in client.get("/api/insights/skills").json())
    assert len(client.get("/api/insights/daily").json()) == 30
    assert len(client.get("/api/insights/daily", params={"dias": 7}).json()) == 7
    assert len(client.get("/api/insights/flow").json()) == 12  # una fuente × 12 semanas


def test_skills_without_profile_empty(client):
    assert client.get("/api/insights/skills").json() == []
