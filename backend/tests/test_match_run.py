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


def test_candidates_beyond_preselect_window(session, session_factory, saved_profile):
    # Muchas ofertas fuera de CR, muy parecidas al perfil, no deben tapar a la que sí aplica.
    src = Source(key="greenhouse:y", nombre="Y", tipo="ats", config_json={})
    session.add(src)
    session.flush()
    similar = "Backend Developer Spring Boot Java Developer"
    for i in range(450):
        session.add(Job(source_id=src.id, titulo=similar, empresa="US Corp", ubicacion="New York, NY",
                        modalidad="presencial", pais=None, url=f"us{i}", hash=f"us{i}", raw_json={},
                        descripcion=similar))
    session.add(Job(source_id=src.id, titulo="Analista QA", empresa="Tica", ubicacion="Heredia, Costa Rica",
                    modalidad="hibrido", provincia="Heredia", pais="CR", url="cr", hash="cr", raw_json={},
                    descripcion="pruebas manuales"))
    session.commit()
    result = run(session_factory, FakeLLMProvider([OK]))
    assert (result.candidatas, result.evaluadas) == (1, 1)


def test_no_candidates(session, session_factory, jobs, saved_profile):
    run(session_factory, FakeLLMProvider([OK] * 5))
    fake = FakeLLMProvider([])
    result = run(session_factory, fake)
    assert (result.candidatas, result.evaluadas) == (0, 0) and fake.calls == []


def test_preselect_not_truncated_by_hnsw(session, saved_profile):
    # Con el índice HNSW, pgvector filtra DESPUÉS del escaneo y ef_search limita las filas:
    # forzamos ese plan y comprobamos que la preselección igual devuelve todas las que aplican.
    from sqlalchemy import text

    from moneyplease.matching.run import _preselect

    src = Source(key="greenhouse:z", nombre="Z", tipo="ats", config_json={})
    session.add(src)
    session.flush()
    emb = FakeEmbedder()
    for i in range(60):
        cr = i % 6 == 0
        session.add(Job(source_id=src.id, titulo=f"Dev {i}", empresa="E", ubicacion="X", url=f"z{i}",
                        hash=f"z{i}", raw_json={}, modalidad="hibrido" if cr else "presencial",
                        pais="CR" if cr else None, embedding=emb.embed([f"dev {i}"])[0]))
    session.commit()
    session.execute(text("SET enable_seqscan = off"))
    session.execute(text("SET hnsw.ef_search = 1"))
    session.execute(text("SET enable_sort = off"))
    rows = _preselect(session, saved_profile.id, saved_profile.embedding, remoto_abierto=True)
    session.execute(text("RESET enable_seqscan"))
    session.execute(text("RESET hnsw.ef_search"))
    session.execute(text("RESET enable_sort"))
    assert len(rows) == 10


def test_aborts_after_consecutive_network_errors(session, session_factory, jobs, saved_profile):
    import httpx

    fake = FakeLLMProvider([httpx.ConnectError("caída")] * 5)
    result = run(session_factory, fake)
    assert result.fallidas == 3 and len(fake.calls) == 3
    assert "red" in result.error


class FailingEmbedder:
    def embed(self, texts):
        raise RuntimeError("descarga del modelo falló")


class SelectiveLLM:
    """Responde OK salvo para las ofertas cuyo título contiene `bad`."""

    model = "fake"

    def __init__(self, bad):
        self.bad, self.calls = bad, 0

    def generate_json(self, system, user, schema):
        self.calls += 1
        if self.bad in user:
            raise LLMError("respuesta rota")
        return OK


def test_error_always_recorded(session, session_factory, jobs, saved_profile):
    from moneyplease.db.models import MatchRun

    result = run_match(session_factory, FailingEmbedder(), FakeLLMProvider([]), now=lambda: NOW)
    assert "descarga del modelo" in result.error
    session.expire_all()
    assert session.scalars(select(MatchRun)).one().error == result.error


def test_limit_above_top_k(session, session_factory, jobs, saved_profile):
    assert run(session_factory, FakeLLMProvider([OK] * 5), top_k=2, max_evals=5).evaluadas == 5


def test_llm_error_resets_network_counter(session, session_factory, jobs, saved_profile):
    import httpx

    net = httpx.ConnectError("caída")
    fake = FakeLLMProvider([net, net, LLMError("a"), LLMError("b"), net, OK])
    result = run(session_factory, fake)
    assert result.error is None and result.evaluadas == 1 and result.fallidas == 4


def test_repeated_failures_skipped_after_three(session, session_factory, jobs, saved_profile):
    llm = SelectiveLLM("QA Engineer")
    first = run(session_factory, llm)
    assert (first.evaluadas, first.fallidas) == (4, 1)
    for _ in range(2):
        assert run(session_factory, llm).fallidas == 1
    calls_before = llm.calls
    fourth = run(session_factory, llm)
    assert fourth.candidatas == 0 and llm.calls == calls_before


def test_new_profile_retries_failed_jobs(session, session_factory, jobs, saved_profile):
    llm = SelectiveLLM("QA Engineer")
    for _ in range(3):
        run(session_factory, llm)
    store.save(session, profile(), "cv", FakeEmbedder())
    assert run(session_factory, SelectiveLLM("nada")).evaluadas == 5
