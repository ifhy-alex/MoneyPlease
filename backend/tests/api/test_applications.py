from datetime import UTC, datetime, timedelta

from moneyplease.api.routes.applications import needs_followup
from moneyplease.db.models import Application
from tests.api.conftest import NOW


def make_app(estado="aplicada", desde=NOW, hasta=None):
    return Application(job_id=1, estado=estado, estado_desde=desde, recordatorio_hasta=hasta,
                       creado_en=desde, actualizado_en=desde)


def test_followup_after_10_days():
    assert needs_followup(make_app(desde=NOW - timedelta(days=10)), NOW, 10)
    assert not needs_followup(make_app(desde=NOW - timedelta(days=9)), NOW, 10)


def test_followup_respects_snooze():
    app = make_app(desde=NOW - timedelta(days=20), hasta=NOW + timedelta(days=1))
    assert not needs_followup(app, NOW, 10)
    app.recordatorio_hasta = NOW - timedelta(seconds=1)
    assert needs_followup(app, NOW, 10)


def test_followup_only_aplicada():
    assert not needs_followup(make_app(estado="entrevista", desde=NOW - timedelta(days=30)), NOW, 10)


def test_create_and_duplicate_409(client, world):
    j = world.job()
    resp = client.post("/api/applications", json={"job_id": j.id})
    assert resp.status_code == 201 and resp.json()["estado"] == "guardada"
    assert resp.json()["job"]["titulo"] == j.titulo
    assert client.post("/api/applications", json={"job_id": j.id}).status_code == 409


def test_create_unknown_job_404(client):
    assert client.post("/api/applications", json={"job_id": 99999}).status_code == 404


def test_patch_state_updates_estado_desde_and_fecha(client, world):
    j = world.job()
    created = client.post("/api/applications", json={"job_id": j.id}).json()
    resp = client.patch(f"/api/applications/{created['id']}", json={"estado": "aplicada", "notas": "Enviado"})
    body = resp.json()
    assert resp.status_code == 200 and body["estado"] == "aplicada" and body["notas"] == "Enviado"
    assert body["fecha_aplicacion"] is not None
    assert body["estado_desde"] >= created["estado_desde"]


def test_patch_keeps_existing_fecha(client, world):
    j = world.job()
    created = client.post("/api/applications", json={"job_id": j.id}).json()
    client.patch(f"/api/applications/{created['id']}", json={"fecha_aplicacion": "2026-10-01"})
    body = client.patch(f"/api/applications/{created['id']}", json={"estado": "aplicada"}).json()
    assert body["fecha_aplicacion"] == "2026-10-01"


def test_patch_invalid_state_422(client, world):
    created = client.post("/api/applications", json={"job_id": world.job().id}).json()
    assert client.patch(f"/api/applications/{created['id']}", json={"estado": "ganada"}).status_code == 422


def test_patch_unknown_404(client):
    assert client.patch("/api/applications/99999", json={"notas": "x"}).status_code == 404


def test_list_with_followup(client, world):
    j = world.job()
    world.session.add(Application(job_id=j.id, estado="aplicada", estado_desde=datetime.now(UTC) - timedelta(days=12),
                                  creado_en=NOW, actualizado_en=NOW))
    world.session.commit()
    body = client.get("/api/applications").json()
    assert body[0]["seguimiento"] is True and body[0]["dias_en_estado"] >= 12


def test_delete(client, world):
    created = client.post("/api/applications", json={"job_id": world.job().id}).json()
    assert client.delete(f"/api/applications/{created['id']}").status_code == 204
    assert client.get("/api/applications").json() == []
    assert client.delete(f"/api/applications/{created['id']}").status_code == 404
