from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select

from moneyplease.api.app import create_app
from moneyplease.api.routes.applications import needs_followup
from moneyplease.config import Settings
from moneyplease.db.models import Application, Job, JobLabel, Match, Profile, Source
from moneyplease.demo import seed

NOW = datetime(2026, 10, 30, 18, tzinfo=UTC)


def test_seed_deterministic(session, session_factory):
    first = seed(session_factory, NOW)
    titles_1 = sorted(session.scalars(select(Job.titulo)).all())
    session.rollback()  # liberar los locks de lectura: seed hace TRUNCATE
    second = seed(session_factory, NOW)
    session.expire_all()
    assert first == second
    assert sorted(session.scalars(select(Job.titulo)).all()) == titles_1
    assert first["jobs"] >= 55 and first["sources"] == 5 and first["profiles"] == 2


def test_seed_covers_states_and_weeks(session, session_factory):
    seed(session_factory, NOW)
    estados = set(session.scalars(select(Application.estado)).all())
    assert estados == {"guardada", "aplicada", "entrevista", "oferta", "rechazada"}
    weeks = {j.primera_vez_visto.isocalendar()[:2] for j in session.scalars(select(Job))}
    assert len(weeks) >= 12
    assert any(needs_followup(a, NOW, 10) for a in session.scalars(select(Application)))
    labels = session.scalars(select(JobLabel.etiqueta)).all()
    assert labels.count("buena") == 6 and labels.count("mala") == 6
    assert session.query(Match).count() >= 40
    assert all(len(p.embedding) == 384 for p in session.scalars(select(Profile)))
    assert all("." not in s.key or ":" in s.key for s in session.scalars(select(Source)))


def test_demo_api_flags(session, session_factory, tmp_path):
    settings = Settings(_env_file=None, demo_mode=True, gemini_api_key="k", private_dir=tmp_path / "p")
    client = TestClient(create_app(settings, session_factory))
    assert client.get("/api/insights").json()["demo"] is True
    resp = client.post("/api/profile/from-cv", files={"archivo": ("cv.pdf", b"%PDF-1.4", "application/pdf")})
    assert resp.status_code == 503
    assert not (tmp_path / "p").exists()
