from datetime import UTC, datetime, timedelta

from moneyplease.db.models import IngestRun, Job, Source
from moneyplease.stats import collect, render

NOW = datetime(2026, 10, 30, 12, tzinfo=UTC)


def add_job(session, source, title, pais=None, first_seen=NOW, estado="active"):
    session.add(Job(source_id=source.id, titulo=title, empresa="E", ubicacion="", descripcion="", url="u",
                    hash=title, raw_json={}, pais=pais, estado=estado,
                    primera_vez_visto=first_seen, ultima_vez_visto=first_seen))


def add_run(session, source, minutes_ago, ok=True, traidas=1):
    t = NOW - timedelta(minutes=minutes_ago)
    session.add(IngestRun(source_id=source.id, iniciado_en=t, terminado_en=t, ok=ok, ofertas_traidas=traidas))


def make_sources(session):
    a = Source(key="greenhouse:a", nombre="A", tipo="ats", config_json={})
    b = Source(key="lever:b", nombre="B", tipo="ats", config_json={})
    session.add_all([a, b])
    session.flush()
    return a, b


def test_stats_counts(session):
    a, b = make_sources(session)
    add_job(session, a, "1", pais="CR")
    add_job(session, a, "2", pais="CR", first_seen=NOW - timedelta(hours=30))
    add_job(session, a, "3")
    add_job(session, a, "4", pais="CR", estado="expired")
    add_job(session, b, "5")
    add_run(session, a, 10)
    session.commit()
    rows = {r.key: r for r in collect(session, NOW)}
    ra = rows["greenhouse:a"]
    assert (ra.ofertas_activas, ra.nuevas_24h, ra.en_cr) == (3, 2, 2)
    assert ra.ultima_corrida_ok is True
    assert rows["lever:b"].ultima_corrida_ok is None


def test_stats_zero_two_runs(session):
    a, b = make_sources(session)
    add_run(session, a, 30, traidas=0)
    add_run(session, a, 20, traidas=0)
    add_run(session, b, 30, traidas=0)
    add_run(session, b, 20, traidas=5)
    add_run(session, b, 10, ok=False, traidas=0)
    session.commit()
    rows = {r.key: r for r in collect(session, NOW)}
    assert rows["greenhouse:a"].cero_en_dos_ultimas is True
    assert rows["lever:b"].cero_en_dos_ultimas is False
    assert rows["lever:b"].ultima_corrida_ok is False


def test_render_has_totals(session):
    a, _ = make_sources(session)
    add_run(session, a, 30, traidas=0)
    add_run(session, a, 20, traidas=0)
    session.commit()
    text = render(collect(session, NOW))
    assert "TOTAL" in text
    assert "greenhouse:a" in text.split("TOTAL")[1]
