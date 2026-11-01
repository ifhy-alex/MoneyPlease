import pytest
from fastapi.testclient import TestClient

from moneyplease.api import deps
from moneyplease.api.app import create_app
from moneyplease.matching.llm import QuotaExceeded
from moneyplease.profile import store as store_mod
from moneyplease.profile.schema import DEFAULT_PREFERENCES
from tests.fakes import FakeEmbedder, FakeLLMProvider
from tests.test_extract import CV
from tests.test_profile_store import DRAFT

PROFILE = {**DRAFT, "preferences": DEFAULT_PREFERENCES.model_dump()}
PDF = ("cv.pdf", b"%PDF-1.4 fake", "application/pdf")


@pytest.fixture
def api(session, session_factory, settings, monkeypatch):
    def build(llm=None, settings_override=None):
        app = create_app(settings_override or settings, session_factory)
        app.dependency_overrides[deps.get_embedder] = lambda: FakeEmbedder()
        if llm is not None:
            app.dependency_overrides[deps.get_llm] = lambda: llm
        monkeypatch.setattr(store_mod, "pdf_text", lambda path: CV)
        return TestClient(app)
    return build


def versions(client):
    return client.get("/api/profile/versions").json()


def test_get_profile_404_then_ok(api):
    client = api()
    assert client.get("/api/profile").status_code == 404
    assert client.put("/api/profile", json=PROFILE).status_code == 201
    body = client.get("/api/profile").json()
    assert body["version"] == 1 and body["perfil"]["experience_months"] == 5


def test_put_invalid_422_no_write(api):
    client = api()
    bad = {**PROFILE, "preferences": {**PROFILE["preferences"], "modalidad": ["remote"]}}
    resp = client.put("/api/profile", json=bad)
    assert resp.status_code == 422
    assert any(e["loc"][-3:-1] == ["preferences", "modalidad"] or "modalidad" in e["loc"]
               for e in resp.json()["detail"])
    assert versions(client) == []


def test_put_twice_versions_increment(api):
    client = api()
    client.put("/api/profile", json=PROFILE)
    assert client.put("/api/profile", json=PROFILE).json()["version"] == 2


def test_versions_desc_with_areas(api):
    client = api()
    perfil = {**PROFILE, "skills": [{"name": "Spring Boot", "level": "intermedio"},
                                    {"name": "Docker", "level": "basico"}]}
    client.put("/api/profile", json=PROFILE)
    client.put("/api/profile", json=perfil)
    body = versions(client)
    assert [v["version"] for v in body] == [2, 1]
    assert body[0]["areas"]["backend"] == 2 and body[0]["areas"]["cloud"] == 1
    assert set(body[0]["areas"]) == {"backend", "frontend", "datos", "cloud", "testing", "idiomas"}


def test_from_cv_returns_draft_not_saved(api, settings):
    client = api(llm=FakeLLMProvider([DRAFT]))
    resp = client.post("/api/profile/from-cv", files={"archivo": PDF})
    assert resp.status_code == 200
    body = resp.json()
    assert body["perfil"]["skills"][0]["name"] == "Spring Boot"
    assert "@" not in body["texto_enviado"] and "Juana" not in body["texto_enviado"]
    assert versions(client) == []
    assert (settings.private_dir / "cv.pdf").exists() and (settings.private_dir / "cv.txt").exists()


def test_from_cv_no_key_503(api):
    resp = api().post("/api/profile/from-cv", files={"archivo": PDF})
    assert resp.status_code == 503 and "GEMINI_API_KEY" in resp.json()["detail"]


def test_from_cv_not_pdf_422(api):
    resp = api(llm=FakeLLMProvider([])).post("/api/profile/from-cv", files={"archivo": ("a.txt", b"hola", "text/plain")})
    assert resp.status_code == 422


def test_from_cv_too_big_422(api):
    big = ("cv.pdf", b"%PDF" + b"0" * (5 * 1024 * 1024 + 1), "application/pdf")
    assert api(llm=FakeLLMProvider([])).post("/api/profile/from-cv", files={"archivo": big}).status_code == 422


def test_from_cv_quota_429(api):
    resp = api(llm=FakeLLMProvider([QuotaExceeded("x")])).post("/api/profile/from-cv", files={"archivo": PDF})
    assert resp.status_code == 429


def test_from_cv_demo_503(api, settings):
    demo = settings.model_copy(update={"demo_mode": True, "gemini_api_key": "k"})
    resp = api(llm=FakeLLMProvider([DRAFT]), settings_override=demo).post("/api/profile/from-cv", files={"archivo": PDF})
    assert resp.status_code == 503 and "demo" in resp.json()["detail"].lower()


def _active_cv(session):
    session.expire_all()
    return store_mod.active(session).cv_texto


def test_put_usa_el_cv_txt_mas_reciente(api, session, settings):
    from tests.test_profile_store import profile
    store_mod.save(session, profile(), "viejo", FakeEmbedder())
    settings.private_dir.mkdir(parents=True, exist_ok=True)
    (settings.private_dir / "cv.txt").write_text("nuevo", encoding="utf-8")
    assert api().put("/api/profile", json=PROFILE).status_code == 201
    assert _active_cv(session) == "nuevo"


def test_put_ignora_cv_txt_anterior_a_la_version(api, session, settings):
    import os

    from tests.test_profile_store import profile
    store_mod.save(session, profile(), "viejo", FakeEmbedder())
    settings.private_dir.mkdir(parents=True, exist_ok=True)
    cv_txt = settings.private_dir / "cv.txt"
    cv_txt.write_text("nuevo", encoding="utf-8")
    os.utime(cv_txt, (0, 0))
    assert api().put("/api/profile", json=PROFILE).status_code == 201
    assert _active_cv(session) == "viejo"
