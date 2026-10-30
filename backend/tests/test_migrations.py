import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from moneyplease.db.models import Job, Source


def test_tables_exist(session):
    names = inspect(session.bind).get_table_names()
    assert {"sources", "jobs", "ingest_runs"} <= set(names)


def test_vector_extension(session):
    exts = session.execute(text("SELECT extname FROM pg_extension")).scalars().all()
    assert "vector" in exts


def test_job_hash_unique(session):
    src = Source(key="lever:x", nombre="X", tipo="ats", config_json={})
    session.add(src)
    session.flush()
    for _ in range(2):
        session.add(Job(source_id=src.id, titulo="t", empresa="e", ubicacion="", descripcion="",
                        url="u", hash="h", raw_json={}))
    with pytest.raises(IntegrityError):
        session.flush()
