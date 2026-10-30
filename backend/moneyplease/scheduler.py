from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from moneyplease.config import Settings, get_settings
from moneyplease.db.session import make_session
from moneyplease.ingest.run import run_ingest


def ingest_job(**kwargs) -> None:
    run_ingest(make_session(), get_settings(), **kwargs)


def build_scheduler(settings: Settings) -> BlockingScheduler:
    sched = BlockingScheduler(timezone=settings.timezone)
    common = {"coalesce": True, "max_instances": 1, "misfire_grace_time": 3600}
    sched.add_job(ingest_job, CronTrigger(hour="6,18", minute=0, timezone=settings.timezone),
                  id="ingesta", kwargs={"exclude": {"jsearch"}}, **common)
    sched.add_job(ingest_job, CronTrigger(hour=6, minute=5, timezone=settings.timezone),
                  id="jsearch", kwargs={"only": "jsearch"}, **common)
    return sched
