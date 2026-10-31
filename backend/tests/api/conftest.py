from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from moneyplease.api.app import create_app
from moneyplease.config import Settings
from moneyplease.db.models import Job, Match, Source
from moneyplease.profile import store
from tests.fakes import FakeEmbedder
from tests.test_profile_store import profile

NOW = datetime(2026, 10, 30, 18, tzinfo=UTC)


class World:
    def __init__(self, session):
        self.session = session
        self.source = Source(key="greenhouse:x", nombre="X", tipo="ats", config_json={})
        session.add(self.source)
        session.commit()
        self.n = 0

    def profile(self):
        return store.save(self.session, profile(), "cv", FakeEmbedder())

    def job(self, **kw):
        self.n += 1
        data = dict(source_id=self.source.id, titulo=f"Job {self.n}", empresa="ACME", ubicacion="Heredia",
                    modalidad="hibrido", pais="CR", provincia="Heredia", url=f"https://x/{self.n}",
                    hash=f"h{self.n}", raw_json={}, descripcion="desc", primera_vez_visto=NOW,
                    ultima_vez_visto=NOW)
        data.update(kw)
        job = Job(**data)
        self.session.add(job)
        self.session.commit()
        return job

    def match(self, prof, job, score=70, fit="junior", **kw):
        m = Match(profile_id=prof.id, job_id=job.id, score=score, fit=fit,
                  fortalezas=kw.pop("fortalezas", ["Java"]), brechas=kw.pop("brechas", ["Docker"]),
                  resumen="ok", modelo="m", evaluado_en=kw.pop("evaluado_en", NOW), **kw)
        self.session.add(m)
        self.session.commit()
        return m


@pytest.fixture
def settings(tmp_path):
    return Settings(_env_file=None, gemini_api_key=None, private_dir=tmp_path / "private")


@pytest.fixture
def client(session, session_factory, settings):
    return TestClient(create_app(settings, session_factory))


@pytest.fixture
def world(session):
    return World(session)
