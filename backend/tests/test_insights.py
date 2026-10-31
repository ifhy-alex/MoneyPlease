from datetime import UTC, datetime, timedelta

import pytest

from moneyplease import insights
from moneyplease.db.models import Job, Match, Source
from moneyplease.profile import store
from tests.fakes import FakeEmbedder
from tests.test_profile_store import profile

NOW = datetime(2026, 10, 30, 18, tzinfo=UTC)


@pytest.fixture
def world(session):
    srcs = {}
    for key in ("greenhouse:x", "workday:hpe", "workday:abbott"):
        s = Source(key=key, nombre=key, tipo="ats", config_json={})
        session.add(s)
        srcs[key] = s
    session.flush()
    prof = store.save(session, profile(), "cv", FakeEmbedder())

    def job(title, source="greenhouse:x", seen=NOW):
        j = Job(source_id=srcs[source].id, titulo=title, empresa="E", url=title, hash=title, raw_json={},
                primera_vez_visto=seen, ultima_vez_visto=seen)
        session.add(j)
        session.flush()
        return j

    def match(j, score=70, fortalezas=(), brechas=(), when=NOW):
        session.add(Match(profile_id=prof.id, job_id=j.id, score=score, fit="junior", fortalezas=list(fortalezas),
                          brechas=list(brechas), resumen="", modelo="m", evaluado_en=when))
        session.flush()
    return prof, job, match


def test_gaps_week_groups_and_ignores_old(session, world):
    prof, job, match = world
    match(job("a"), brechas=["Pide Kubernetes"])
    match(job("b"), brechas=["kubernetes avanzado", "Inglés C1"])
    match(job("c"), brechas=["Pide Kubernetes"], when=NOW - timedelta(days=8))
    gaps = dict(insights.gaps_week(session, prof.id, NOW))
    assert gaps["kubernetes"] == 2
    assert sum(gaps.values()) == 3


def test_gaps_week_empty(session, world):
    prof, _, _ = world
    assert insights.gaps_week(session, prof.id, NOW) == []


def test_skills_tengo_and_brecha(session, world):
    prof, job, match = world
    match(job("a"), fortalezas=["Experiencia con Spring Boot"], brechas=["Pide Kubernetes"])
    rows = {r["skill"]: r for r in insights.skills(session, profile(), prof.id)}
    assert rows["spring boot"]["tengo"] is True and rows["spring boot"]["area"] == "backend"
    assert rows["kubernetes"]["brecha"] is True and rows["kubernetes"]["tengo"] is False
    assert rows["kubernetes"]["frecuencia"] == 1


def test_skills_from_profile_only(session, world):
    prof, _, _ = world
    rows = {r["skill"]: r for r in insights.skills(session, profile(), prof.id)}
    assert rows["spring boot"]["frecuencia"] == 1 and rows["spring boot"]["tengo"] is True


def test_daily_costa_rica_days(session, world):
    prof, job, match = world
    late = datetime(2026, 10, 30, 1, tzinfo=UTC)  # 19:00 del 29 en Costa Rica
    match(job("a", seen=late), score=80)
    days = insights.daily(session, prof.id, NOW, dias=30)
    assert len(days) == 30
    by_date = {d["fecha"]: d for d in days}
    assert by_date["2026-10-29"]["nuevas"] == 1 and by_date["2026-10-29"]["score_promedio"] == 80
    assert by_date["2026-10-30"]["nuevas"] == 0 and by_date["2026-10-30"]["score_promedio"] is None


def test_flow_groups_by_connector(session, world):
    _, job, _ = world
    job("a", source="workday:hpe")
    job("b", source="workday:abbott")
    job("c")
    rows = insights.flow(session, NOW, semanas=12)
    fuentes = {r["fuente"] for r in rows}
    assert fuentes == {"greenhouse", "workday"}
    assert len(rows) == 12 * 2
    this_week = max(r["semana"] for r in rows)
    assert sum(r["nuevas"] for r in rows if r["semana"] == this_week and r["fuente"] == "workday") == 2
