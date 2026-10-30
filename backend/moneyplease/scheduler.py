import logging

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from moneyplease.config import Settings, get_settings
from moneyplease.db.session import make_session
from moneyplease.ingest.run import run_ingest
from moneyplease.matching.factory import build_embedder, build_llm
from moneyplease.matching.run import run_match

log = logging.getLogger(__name__)


def ingest_job(**kwargs) -> None:
    settings = get_settings()
    run_ingest(make_session(), settings, **kwargs)
    if "only" in kwargs:
        return  # las ofertas de jsearch se evalúan en la siguiente corrida de ingesta
    if not settings.gemini_api_key:
        log.info("Sin GEMINI_API_KEY; matching omitido")
        return
    run_match(make_session(), build_embedder(), build_llm(settings),
              top_k=settings.match_top_k, max_evals=settings.match_max_evals)


def build_scheduler(settings: Settings) -> BlockingScheduler:
    # Un solo hilo: las corridas (ingesta, jsearch y matching) nunca se solapan.
    sched = BlockingScheduler(timezone=settings.timezone, executors={"default": ThreadPoolExecutor(1)})
    common = {"coalesce": True, "max_instances": 1, "misfire_grace_time": 3600}
    sched.add_job(ingest_job, CronTrigger(hour="6,18", minute=0, timezone=settings.timezone),
                  id="ingesta", kwargs={"exclude": {"jsearch"}}, **common)
    sched.add_job(ingest_job, CronTrigger(hour=6, minute=5, timezone=settings.timezone),
                  id="jsearch", kwargs={"only": "jsearch"}, **common)
    return sched
