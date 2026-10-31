from datetime import UTC, datetime

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from moneyplease.db.models import Application
from tests.test_migrations_0002 import make_job

NOW = datetime(2026, 10, 30, tzinfo=UTC)


def test_applications_table(session):
    insp = inspect(session.bind)
    assert "applications" in insp.get_table_names()
    assert "ejemplos_hash" in {c["name"] for c in insp.get_columns("matches")}


def test_application_job_unique(session):
    job = make_job(session)
    for _ in range(2):
        session.add(Application(job_id=job.id, estado="guardada", estado_desde=NOW, creado_en=NOW, actualizado_en=NOW))
    with pytest.raises(IntegrityError):
        session.flush()


def test_unaccent_available(session):
    assert session.execute(text("SELECT unaccent('José')")).scalar() == "Jose"
