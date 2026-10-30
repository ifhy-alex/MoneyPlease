from moneyplease import __main__ as cli
from moneyplease.scheduler import build_scheduler
from moneyplease.config import Settings


def test_scheduler_jobs():
    sched = build_scheduler(Settings(_env_file=None))
    jobs = {j.id: j for j in sched.get_jobs()}
    assert set(jobs) == {"ingesta", "jsearch"}
    ingesta = {f.name: str(f) for f in jobs["ingesta"].trigger.fields}
    js = {f.name: str(f) for f in jobs["jsearch"].trigger.fields}
    assert ingesta["hour"] == "6,18" and ingesta["minute"] == "0"
    assert js["hour"] == "6" and js["minute"] == "5"
    assert str(jobs["ingesta"].trigger.timezone) == "America/Costa_Rica"
    assert jobs["ingesta"].kwargs == {"exclude": {"jsearch"}}
    assert jobs["jsearch"].kwargs == {"only": "jsearch"}
    assert jobs["ingesta"].max_instances == 1 and jobs["ingesta"].coalesce


def test_cli_ingest_calls_run(monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "make_session", lambda: "factory")
    monkeypatch.setattr(cli, "run_ingest", lambda factory, settings, only=None: calls.append((factory, only)) or [])
    cli.main(["ingest", "--source", "lever:x"])
    assert calls == [("factory", "lever:x")]
