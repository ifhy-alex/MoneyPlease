from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

from moneyplease.db.models import Job, Match, Source
from moneyplease.matching.llm import LLMError, QuotaExceeded
from moneyplease.matching.run import run_match
from moneyplease.profile import store
from tests.fakes import FakeEmbedder, FakeLLMProvider
from tests.test_profile_store import profile

OK = {"score": 75, "fit": "junior", "fortalezas": ["Java"], "brechas": [], "resumen": "ok"}
NOW = datetime(2026, 10, 30, 12, tzinfo=UTC)
TITLES = ["Backend Developer", "Java Developer", "Data Engineer", "QA Engineer", "Senior Java Engineer",
          "Software Intern"]


@pytest.fixture
def jobs(session):
    src = Source(key="greenhouse:x", nombre="X", tipo="ats", config_json={})
    session.add(src)
    session.flush()
    for i, title in enumerate(TITLES):
        session.add(Job(source_id=src.id, titulo=title, empresa="ACME", ubicacion="Heredia, Costa Rica",
                        modalidad="hibrido", provincia="Heredia", pais="CR", url=f"u{i}", hash=f"h{i}",
                        raw_json={}, descripcion="" if title == "Software Intern" else "Java Spring Boot"))
    session.commit()


@pytest.fixture
def saved_profile(session):
    return store.save(session, profile(), "cv", FakeEmbedder())


def run(session_factory, llm, **kw):
    return run_match(session_factory, FakeEmbedder(), llm, now=lambda: NOW, **kw)


def count_matches(session):
    session.expire_all()
    return session.scalar(select(func.count()).select_from(Match))


def test_no_profile_returns_none(session, session_factory, jobs):
    assert run(session_factory, FakeLLMProvider([])) is None


def test_embeds_missing_only(session, session_factory, jobs, saved_profile):
    first = run(session_factory, FakeLLMProvider([OK] * 5))
    second = run(session_factory, FakeLLMProvider([]))
    assert (first.embebidas, second.embebidas) == (6, 0)


def test_filters_then_evaluates(session, session_factory, jobs, saved_profile):
    fake = FakeLLMProvider([OK] * 5)
    result = run(session_factory, fake)
    assert (result.candidatas, result.evaluadas, result.fallidas) == (5, 5, 0)
    assert not any("Senior Java Engineer" in user for _, user, _ in fake.calls)


def test_empty_description_evaluated(session, session_factory, jobs, saved_profile):
    run(session_factory, FakeLLMProvider([OK] * 5))
    intern = session.scalars(select(Job).where(Job.titulo == "Software Intern")).one()
    assert session.get(Match, (saved_profile.id, intern.id)) is not None


def test_cache_skips_evaluated(session, session_factory, jobs, saved_profile):
    run(session_factory, FakeLLMProvider([OK] * 5))
    fake = FakeLLMProvider([])
    result = run(session_factory, fake)
    assert result.candidatas == 0 and fake.calls == []


def test_new_profile_reevaluates(session, session_factory, jobs, saved_profile):
    run(session_factory, FakeLLMProvider([OK] * 5))
    store.save(session, profile(), "cv", FakeEmbedder())
    assert run(session_factory, FakeLLMProvider([OK] * 5)).evaluadas == 5
    assert count_matches(session) == 10


def test_quota_midway(session, session_factory, jobs, saved_profile):
    result = run(session_factory, FakeLLMProvider([OK, OK, QuotaExceeded()]))
    assert result.evaluadas == 2 and result.cuota_agotada is True
    assert count_matches(session) == 2
    assert run(session_factory, FakeLLMProvider([OK] * 3)).evaluadas == 3


def test_max_evals_respected(session, session_factory, jobs, saved_profile):
    assert run(session_factory, FakeLLMProvider([OK] * 5), max_evals=2).evaluadas == 2


def test_llm_error_counts_failed(session, session_factory, jobs, saved_profile):
    result = run(session_factory, FakeLLMProvider([LLMError("a"), LLMError("b")] + [OK] * 4))
    assert (result.fallidas, result.evaluadas) == (1, 4)


def test_no_candidates(session, session_factory, jobs, saved_profile):
    run(session_factory, FakeLLMProvider([OK] * 5))
    fake = FakeLLMProvider([])
    result = run(session_factory, fake)
    assert (result.candidatas, result.evaluadas) == (0, 0) and fake.calls == []
