from datetime import UTC, datetime, timedelta

import pytest

from moneyplease import __main__ as cli
from moneyplease import eval as ev
from moneyplease import scheduler
from moneyplease.config import Settings
from moneyplease.db.models import Job, JobLabel, Match, MatchRun, Source
from moneyplease.profile import store
from moneyplease.stats import collect, match_status, render
from tests.fakes import FakeEmbedder
from tests.test_profile_store import profile

NOW = datetime(2026, 10, 30, 12, tzinfo=UTC)


@pytest.fixture
def setup(session):
    src = Source(key="greenhouse:x", nombre="X", tipo="ats", config_json={})
    session.add(src)
    session.flush()
    prof = store.save(session, profile(), "cv", FakeEmbedder())

    def add(title, score, fit, estado="active", label=None, age_min=0):
        job = Job(source_id=src.id, titulo=title, empresa="ACME", ubicacion="Heredia", modalidad="hibrido",
                  url=f"https://x/{title}", hash=title, raw_json={}, estado=estado)
        session.add(job)
        session.flush()
        session.add(Match(profile_id=prof.id, job_id=job.id, score=score, fit=fit, fortalezas=["Java"],
                          brechas=["Docker"], resumen="ok", modelo="m",
                          evaluado_en=NOW - timedelta(minutes=age_min)))
        if label:
            session.add(JobLabel(job_id=job.id, etiqueta=label))
        session.commit()
        return job
    return prof, add


def test_top_excludes_no_aplica_and_expired(session, setup):
    prof, add = setup
    add("A", 80, "junior")
    add("B", 90, "no_aplica")
    add("C", 70, "junior", estado="expired")
    rows = ev.top_matches(session, prof.id, 10)
    assert [job.titulo for _, job in rows] == ["A"]


def test_top_fit_filter(session, setup):
    prof, add = setup
    add("A", 80, "junior")
    add("B", 60, "practica")
    assert [j.titulo for _, j in ev.top_matches(session, prof.id, 10, fit="practica")] == ["B"]
    assert [j.titulo for _, j in ev.top_matches(session, prof.id, 10, min_score=70)] == ["A"]
    assert [j.titulo for _, j in ev.top_matches(session, prof.id, 10, fit="no_aplica")] == []


def test_render_top_contains_parts(session, setup):
    prof, add = setup
    job = add("A", 80, "junior")
    text = ev.render_top(ev.top_matches(session, prof.id, 10))
    assert f"[{job.id}]" in text and "+ Java" in text and "- Docker" in text and "https://x/A" in text


def test_render_top_empty():
    assert "Sin resultados" in ev.render_top([])


def test_label_upsert_and_unknown_job(session, setup):
    prof, add = setup
    job = add("A", 80, "junior")
    ev.label(session, job.id, "buena")
    ev.label(session, job.id, "mala")
    session.expire_all()
    assert session.get(JobLabel, job.id).etiqueta == "mala"
    with pytest.raises(ValueError):
        ev.label(session, 99999, "buena")


def test_eval_summary_counts(session, setup):
    prof, add = setup
    labels = ["buena", "buena", "buena", "regular", "mala", "mala", None, None, None, None]
    for i, lab in enumerate(labels):
        add(f"J{i}", 90 - i, "junior", label=lab)
    s = ev.summary(session, prof.id)
    assert (s.top10_etiquetadas, s.top10_relevantes) == (6, 4)
    assert s.score_promedio["buena"] == pytest.approx(89.0)
    assert "4/10" in ev.render_summary(s)


def test_stats_shows_match_line(session, setup):
    prof, _ = setup
    session.add(MatchRun(profile_id=prof.id, iniciado_en=NOW, terminado_en=NOW, candidatas=3, evaluadas=1,
                         fallidas=0, cuota_agotada=True))
    session.commit()
    text = render(collect(session, NOW), match_status(session))
    assert "cuota agotada" in text and "candidatas=3" in text


def test_cli_match_without_key_exits_2(monkeypatch):
    monkeypatch.setattr(cli, "get_settings", lambda: Settings(_env_file=None, gemini_api_key=None))
    with pytest.raises(SystemExit) as exc:
        cli.main(["match"])
    assert exc.value.code == 2


def test_scheduler_ingest_runs_match(monkeypatch):
    calls = []
    monkeypatch.setattr(scheduler, "run_ingest", lambda *a, **k: [])
    monkeypatch.setattr(scheduler, "run_match", lambda *a, **k: calls.append(k))
    monkeypatch.setattr(scheduler, "make_session", lambda: "factory")
    monkeypatch.setattr(scheduler, "get_settings", lambda: Settings(_env_file=None, gemini_api_key="k"))
    monkeypatch.setattr(scheduler, "build_embedder", lambda: "emb")
    scheduler.ingest_job(exclude={"jsearch"})
    assert len(calls) == 1
    scheduler.ingest_job(only="jsearch")
    assert len(calls) == 1


def test_scheduler_skips_match_without_key(monkeypatch):
    calls = []
    monkeypatch.setattr(scheduler, "run_ingest", lambda *a, **k: [])
    monkeypatch.setattr(scheduler, "run_match", lambda *a, **k: calls.append(k))
    monkeypatch.setattr(scheduler, "make_session", lambda: "factory")
    monkeypatch.setattr(scheduler, "get_settings", lambda: Settings(_env_file=None, gemini_api_key=None))
    scheduler.ingest_job(exclude={"jsearch"})
    assert calls == []


def test_stats_pending_candidates(session, setup):
    prof, _ = setup
    src = session.scalars(__import__("sqlalchemy").select(Source)).first()
    emb = FakeEmbedder()
    for i in range(2):
        session.add(Job(source_id=src.id, titulo=f"Dev {i}", empresa="E", ubicacion="Heredia", modalidad="hibrido",
                        provincia="Heredia", pais="CR", url=f"p{i}", hash=f"p{i}", raw_json={},
                        embedding=emb.embed([f"dev {i}"])[0]))
    session.commit()
    status = match_status(session)
    assert status.pendientes == 2
    assert "Candidatas pendientes de evaluar: 2" in render(collect(session, NOW), status)


def test_stats_pending_without_profile(session):
    status = match_status(session)
    assert status.pendientes is None
    assert "pendientes" not in render(collect(session, NOW), status)


@pytest.mark.parametrize("error,text", [
    ("quota", "cuota"),
    ("llm", "respuesta"),
    ("net", "conectar"),
])
def test_from_cv_friendly_errors(monkeypatch, capsys, error, text):
    import httpx

    from moneyplease.matching.llm import LLMError, QuotaExceeded
    from moneyplease.profile import store as store_mod

    exc = {"quota": QuotaExceeded("429"), "llm": LLMError("basura"), "net": httpx.ConnectError("caída")}[error]

    def boom(*a, **k):
        raise exc

    monkeypatch.setattr(cli, "get_settings", lambda: Settings(_env_file=None, gemini_api_key="k"))
    monkeypatch.setattr(store_mod, "from_cv", boom)
    with pytest.raises(SystemExit) as info:
        cli.main(["profile", "from-cv", "x.pdf"])
    assert info.value.code == 1
    out = capsys.readouterr().out.lower()
    assert text in out and "traceback" not in out
