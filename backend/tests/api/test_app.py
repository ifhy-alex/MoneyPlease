from fastapi.testclient import TestClient

from moneyplease.api.app import create_app


def test_spa_fallback(session_factory, settings, tmp_path):
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<div id=\"root\"></div>", encoding="utf-8")
    client = TestClient(create_app(settings, session_factory, static_dir=static))
    resp = client.get("/postulaciones")
    assert resp.status_code == 200 and 'id="root"' in resp.text


def test_unknown_api_404_json(client):
    resp = client.get("/api/no-existe")
    assert resp.status_code == 404 and resp.headers["content-type"].startswith("application/json")
