from datetime import UTC, datetime

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from moneyplease.db.models import Job, Match, Profile, Source

NOW = datetime(2026, 10, 30, tzinfo=UTC)


def make_job(session):
    src = Source(key="lever:x", nombre="X", tipo="ats", config_json={})
    session.add(src)
    session.flush()
    job = Job(source_id=src.id, titulo="t", empresa="e", url="u", hash="h", raw_json={})
    session.add(job)
    session.flush()
    return job


def make_profile(session, version=1):
    p = Profile(version=version, cv_texto="", perfil_json={}, embedding=[0.0] * 384, creado_en=NOW)
    session.add(p)
    session.flush()
    return p


def test_new_tables_exist(session):
    names = set(inspect(session.bind).get_table_names())
    assert {"sources", "jobs", "ingest_runs", "profiles", "matches", "match_runs", "job_labels"} <= names


def test_hnsw_index_exists(session):
    indexdef = session.execute(
        text("SELECT indexdef FROM pg_indexes WHERE indexname = 'ix_jobs_embedding_hnsw'")).scalar()
    assert "hnsw" in indexdef and "vector_cosine_ops" in indexdef


def test_match_pk_composite(session):
    job, prof = make_job(session), make_profile(session)
    for _ in range(2):
        session.add(Match(profile_id=prof.id, job_id=job.id, score=50, fit="junior", fortalezas=[],
                          brechas=[], resumen="", modelo="m", evaluado_en=NOW))
    with pytest.raises(IntegrityError):
        session.flush()


def test_profile_version_unique(session):
    make_profile(session, 1)
    with pytest.raises(IntegrityError):
        make_profile(session, 1)
