import argparse
import logging
import sys
from datetime import UTC, datetime

from moneyplease.config import get_settings
from moneyplease.db.session import make_session
from moneyplease.ingest.run import run_ingest


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="moneyplease")
    sub = parser.add_subparsers(dest="cmd", required=True)
    ingest = sub.add_parser("ingest", help="corre la ingesta una vez")
    ingest.add_argument("--source", help="solo esta fuente, p. ej. greenhouse:konradgroup")
    sub.add_parser("stats", help="ofertas por fuente y estado de las corridas")
    sub.add_parser("gmail-auth", help="autoriza la lectura de Gmail (una sola vez)")
    sub.add_parser("worker", help="arranca el scheduler")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    settings = get_settings()

    if args.cmd == "ingest":
        factory = make_session()
        runs = run_ingest(factory, settings, only=args.source)
        if runs:
            from sqlalchemy import select

            from moneyplease.db.models import Source

            with factory() as session:
                keys = dict(session.execute(select(Source.id, Source.key)).all())
        for run in runs:
            print(f"{keys[run.source_id]:<28} ok={run.ok} traidas={run.ofertas_traidas} nuevas={run.ofertas_nuevas}"
                  + (f" error={run.error}" if run.error else ""))
    elif args.cmd == "stats":
        from moneyplease.stats import collect, render

        with make_session()() as session:
            print(render(collect(session, datetime.now(UTC))))
    elif args.cmd == "gmail-auth":
        from moneyplease.ingest.connectors.gmail_alerts import authorize

        authorize(settings)
        print(f"Token guardado en {settings.gmail_token_path}")
    elif args.cmd == "worker":
        from moneyplease.scheduler import build_scheduler

        sched = build_scheduler(settings)
        for job in sched.get_jobs():
            logging.info("Job %s programado: %s", job.id, job.trigger)
        sched.start()


if __name__ == "__main__":
    main()
