from datetime import UTC, date, datetime, timedelta

import httpx
import pytest
from sqlalchemy import select

from moneyplease.config import Settings
from moneyplease.db.models import IngestRun, Job, Source
from moneyplease.ingest.base import ConnectorResult, QuotaExhausted, RawJob, SourceGone
from moneyplease.ingest.connectors import build_connector
from moneyplease.ingest.http import PoliteClient
from moneyplease.ingest.run import run_ingest

YAML = """
- {nombre: X, ats: greenhouse, slug: x, careers_url: "https://x", activa: true}
- {nombre: Y, ats: lever, slug: y, careers_url: "https://y", activa: true}
"""


def job(title, company="ACME", location="Heredia"):
    return RawJob(external_id=title, title=title, company=company, location=location, description="d",
                  url=f"https://x/{title}", published_at=None, raw={"t": title})


class Fake:
    def __init__(self, key, complete, outcomes):
        self.key, self.is_complete_listing, self.outcomes = key, complete, list(outcomes)

    def fetch(self):
        out = self.outcomes.pop(0)
        if isinstance(out, Exception):
            raise out
        return out if isinstance(out, ConnectorResult) else ConnectorResult(out)


@pytest.fixture
def settings(tmp_path):
    p = tmp_path / "companies.yaml"
    p.write_text(YAML, encoding="utf-8")
    return Settings(_env_file=None, companies_path=p)


class Clock:
    def __init__(self):
        self.t = datetime(2026, 10, 30, 12, tzinfo=UTC)

    def __call__(self):
        self.t += timedelta(minutes=1)
        return self.t


@pytest.fixture
def ingest(session, session_factory, settings):
    clock = Clock()

    def _run(only=None, exclude=None, **fakes):
        conns = {k.replace("__", ":"): v for k, v in fakes.items()}
        return run_ingest(session_factory, settings, only=only, exclude=exclude, now=clock,
                          connector_factory=lambda src, *_: conns.get(src.key))
    return _run


def jobs(session):
    session.expire_all()
    return {j.titulo: j for j in session.scalars(select(Job))}


def source(session, key):
    session.expire_all()
    return session.scalars(select(Source).where(Source.key == key)).one()


def test_inserts_new_jobs(session, ingest):
    runs = ingest(greenhouse__x=Fake("greenhouse:x", True, [[job("A"), job("B")]]))
    assert set(jobs(session)) == {"A", "B"}
    assert all(j.estado == "active" for j in jobs(session).values())
    assert (runs[0].ok, runs[0].ofertas_traidas, runs[0].ofertas_nuevas) == (True, 2, 2)


def test_upsert_same_hash_twice_in_batch(session, ingest):
    runs = ingest(greenhouse__x=Fake("greenhouse:x", True, [[job("A"), job("A")]]))
    assert len(jobs(session)) == 1
    assert runs[0].ok


def test_second_run_updates_not_duplicates(session, ingest):
    f = Fake("greenhouse:x", True, [[job("A")], [job("A")]])
    ingest(greenhouse__x=f)
    first_seen = jobs(session)["A"].ultima_vez_visto
    runs = ingest(greenhouse__x=f)
    assert len(jobs(session)) == 1
    assert runs[0].ofertas_nuevas == 0
    assert jobs(session)["A"].ultima_vez_visto > first_seen


def test_expires_after_two_missing_runs(session, ingest):
    f = Fake("greenhouse:x", True, [[job("A"), job("B")], [job("A")], [job("A")]])
    ingest(greenhouse__x=f)
    ingest(greenhouse__x=f)
    assert jobs(session)["B"].estado == "active" and jobs(session)["B"].corridas_ausente == 1
    ingest(greenhouse__x=f)
    assert jobs(session)["B"].estado == "expired"
    assert jobs(session)["A"].estado == "active"


def test_failed_fetch_does_not_expire(session, ingest):
    f = Fake("greenhouse:x", True, [[job("A")], httpx.ConnectError("x"), httpx.ConnectError("x")])
    for _ in range(3):
        ingest(greenhouse__x=f)
    a = jobs(session)["A"]
    assert a.estado == "active" and a.corridas_ausente == 0


def test_incomplete_listing_never_expires(session, ingest):
    f = Fake("jsearch", False, [[job("A")], [], [], []])
    for _ in range(4):
        ingest(jsearch=f)
    assert jobs(session)["A"].estado == "active"


def test_reactivates_expired(session, ingest):
    f = Fake("greenhouse:x", True, [[job("B")], [], [], [job("B")]])
    for _ in range(3):
        ingest(greenhouse__x=f)
    assert jobs(session)["B"].estado == "expired"
    ingest(greenhouse__x=f)
    b = jobs(session)["B"]
    assert b.estado == "active" and b.corridas_ausente == 0


def test_failure_isolated(session, ingest):
    runs = ingest(greenhouse__x=Fake("greenhouse:x", True, [RuntimeError("boom")]),
                  lever__y=Fake("lever:y", True, [[job("C")]]))
    assert set(jobs(session)) == {"C"}
    failed = [r for r in runs if not r.ok]
    assert len(failed) == 1 and "boom" in failed[0].error


def test_source_gone_deactivates(session, ingest):
    ingest(greenhouse__x=Fake("greenhouse:x", True, [SourceGone("404 https://x")]))
    src = source(session, "greenhouse:x")
    assert src.activa is False and src.desactivada_motivo == "404 https://x"


def test_quota_exhausted_sets_until(session, ingest):
    ingest(jsearch=Fake("jsearch", False, [QuotaExhausted(date(2026, 11, 1))]))
    src = source(session, "jsearch")
    assert src.config_json["quota_exhausted_until"] == "2026-11-01"
    assert src.config_json["queries"]


def test_seen_by_second_source_resets(session, ingest):
    gh = Fake("greenhouse:x", True, [[job("A"), job("B")], [job("B")]])
    ingest(greenhouse__x=gh)
    ingest(greenhouse__x=gh)
    assert jobs(session)["A"].corridas_ausente == 1
    ingest(jsearch=Fake("jsearch", False, [[job("A")]]))
    a = jobs(session)["A"]
    assert len(jobs(session)) == 2
    assert a.source_id == source(session, "greenhouse:x").id and a.corridas_ausente == 0


def test_complete_listing_takes_over_job(session, ingest):
    ingest(jsearch=Fake("jsearch", False, [[job("A")]]))
    gh = Fake("greenhouse:x", True, [[job("A")], [], []])
    for _ in range(3):
        ingest(greenhouse__x=gh)
    a = jobs(session)["A"]
    assert a.source_id == source(session, "greenhouse:x").id
    assert a.estado == "expired"


def test_connector_build_error_isolated(session, session_factory, settings):
    def factory(src, *_):
        if src.key == "greenhouse:x":
            raise RuntimeError("token vencido")
        return Fake("lever:y", True, [[job("C")]]) if src.key == "lever:y" else None

    runs = run_ingest(session_factory, settings, connector_factory=factory, now=Clock())
    assert set(jobs(session)) == {"C"}
    failed = [r for r in runs if not r.ok]
    assert len(failed) == 1 and "token vencido" in failed[0].error
    assert failed[0].source_id == source(session, "greenhouse:x").id


def test_config_updates_merged(session, ingest):
    ingest(jsearch=Fake("jsearch", False, [ConnectorResult([], {"query_index": 3})]))
    src = source(session, "jsearch")
    assert src.config_json["query_index"] == 3 and src.config_json["queries"]


def test_only_and_exclude(session, ingest):
    fakes = dict(greenhouse__x=Fake("greenhouse:x", True, [[job("A")]] * 2),
                 lever__y=Fake("lever:y", True, [[job("B")]] * 2))
    assert [r.source_id for r in ingest(only="lever:y", **fakes)] == [source(session, "lever:y").id]
    assert [r.source_id for r in ingest(exclude={"lever:y"}, **fakes)] == [source(session, "greenhouse:x").id]


def test_runs_recorded(session, ingest):
    ingest(greenhouse__x=Fake("greenhouse:x", True, [[job("A")]]))
    run = session.scalars(select(IngestRun)).one()
    assert run.ok and run.terminado_en >= run.iniciado_en


def test_build_connector_skips_without_credentials(tmp_path):
    s = Settings(_env_file=None, jsearch_api_key=None, gmail_token_path=tmp_path / "nope.json")
    client = PoliteClient()
    assert build_connector(Source(key="jsearch", nombre="j", tipo="api", config_json={}), s, client, date.today()) is None
    assert build_connector(Source(key="gmail", nombre="g", tipo="email", config_json={}), s, client, date.today()) is None


def test_build_connector_respects_quota():
    s = Settings(_env_file=None, jsearch_api_key="k")
    src = Source(key="jsearch", nombre="j", tipo="api", config_json={"quota_exhausted_until": "2026-11-01"})
    assert build_connector(src, s, PoliteClient(), date(2026, 10, 30)) is None
    assert build_connector(src, s, PoliteClient(), date(2026, 11, 1)) is not None


def test_build_connector_ats():
    s = Settings(_env_file=None)
    src = Source(key="lever:y", nombre="Y", tipo="ats", config_json={"slug": "y"})
    c = build_connector(src, s, PoliteClient(), date.today())
    assert c.key == "lever:y" and c.company == "Y"


def test_upsert_refreshes_derived_fields(session, ingest):
    f = Fake("greenhouse:x", True, [[job("A", location="Heredia, Costa Rica")]] * 2)
    ingest(greenhouse__x=f)
    session.execute(Job.__table__.update().values(pais=None, provincia=None, modalidad="x"))
    session.commit()
    ingest(greenhouse__x=f)
    a = jobs(session)["A"]
    assert (a.pais, a.provincia, a.modalidad) == ("CR", "Heredia", "desconocida")
