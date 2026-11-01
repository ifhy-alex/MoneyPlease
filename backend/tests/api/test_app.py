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


def _broken_factory(orig):
    from sqlalchemy.exc import ProgrammingError

    def boom(*args, **kwargs):
        raise ProgrammingError("SELECT", {}, orig)

    class Broken:
        execute = scalars = scalar = get = boom

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    return lambda: Broken()


def test_demo_otro_error_de_sql_no_se_disfraza_de_falta_de_seed(settings):
    import psycopg
    demo = settings.model_copy(update={"demo_mode": True})
    app = create_app(demo, _broken_factory(psycopg.errors.SyntaxError("syntax error at or near")))
    resp = TestClient(app, raise_server_exceptions=False).get("/api/top")
    assert resp.status_code == 500


def test_demo_tabla_inexistente_es_503(settings):
    import psycopg
    demo = settings.model_copy(update={"demo_mode": True})
    app = create_app(demo, _broken_factory(psycopg.errors.UndefinedTable('relation "jobs" does not exist')))
    assert TestClient(app).get("/api/top").status_code == 503
