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
    prof = sub.add_parser("profile", help="perfil generado desde el CV").add_subparsers(dest="action", required=True)
    from_cv = prof.add_parser("from-cv", help="genera private/profile.yaml desde el CV")
    from_cv.add_argument("path")
    from_cv.add_argument("--force", action="store_true")
    prof.add_parser("save", help="guarda private/profile.yaml como versión nueva")
    prof.add_parser("show", help="muestra la versión activa")
    match = sub.add_parser("match", help="evalúa ofertas contra el perfil activo")
    match.add_argument("--limit", type=int, help="máximo de evaluaciones con el LLM")
    top = sub.add_parser("top", help="mejores ofertas del perfil activo")
    top.add_argument("--n", type=int, default=10)
    top.add_argument("--fit", choices=["practica", "junior", "no_aplica"])
    top.add_argument("--min-score", type=int)
    lab = sub.add_parser("label", help="etiqueta una oferta a mano")
    lab.add_argument("job_id", type=int)
    lab.add_argument("etiqueta", choices=["buena", "regular", "mala"])
    sub.add_parser("eval", help="mide el top 10 contra las etiquetas")
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
        from moneyplease.stats import collect, match_status, render

        with make_session()() as session:
            print(render(collect(session, datetime.now(UTC)), match_status(session)))
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
    else:
        _matching_command(args, settings)


def _require_llm(settings):
    from moneyplease.matching.factory import build_llm

    try:
        return build_llm(settings)
    except RuntimeError as exc:
        print(exc)
        sys.exit(2)


def _matching_command(args, settings) -> None:
    from pathlib import Path

    import yaml

    from moneyplease import eval as ev
    from moneyplease.matching.factory import build_embedder
    from moneyplease.profile import store

    private = settings.private_dir
    no_profile = "No hay perfil guardado: corre `profile from-cv` y `profile save` primero."
    if args.cmd == "match":
        llm = _require_llm(settings)
        from moneyplease.matching.run import run_match

        limit = args.limit if args.limit is not None else settings.match_max_evals
        run = run_match(make_session(), build_embedder(), llm, top_k=settings.match_top_k, max_evals=limit)
        if run is None:
            print(no_profile)
        else:
            print(f"embebidas={run.embebidas} candidatas={run.candidatas} evaluadas={run.evaluadas} "
                  f"fallidas={run.fallidas}" + (" · cuota agotada" if run.cuota_agotada else ""))
        return
    if args.cmd == "profile" and args.action == "from-cv":
        try:
            out = store.from_cv(Path(args.path), private, _require_llm(settings), args.force)
        except FileExistsError as exc:
            print(exc)
            sys.exit(1)
        print(f"Borrador escrito en {out}. Revísalo y luego corre `profile save`.")
        return
    with make_session()() as session:
        if args.cmd == "profile" and args.action == "save":
            try:
                profile = store.read_yaml(private / "profile.yaml")
            except (store.ProfileError, FileNotFoundError) as exc:
                print(exc)
                sys.exit(1)
            cv_path = private / "cv.txt"
            cv_text = cv_path.read_text(encoding="utf-8") if cv_path.exists() else ""
            row = store.save(session, profile, cv_text, build_embedder())
            print(f"Versión {row.version} guardada")
            return
        active = store.active(session)
        if active is None:
            print(no_profile)
            sys.exit(1)
        if args.cmd == "profile":
            print(f"# versión {active.version}\n"
                  + yaml.safe_dump(active.perfil_json, allow_unicode=True, sort_keys=False))
        elif args.cmd == "top":
            print(ev.render_top(ev.top_matches(session, active.id, args.n, args.fit, args.min_score)))
        elif args.cmd == "label":
            try:
                ev.label(session, args.job_id, args.etiqueta)
            except ValueError as exc:
                print(exc)
                sys.exit(1)
            print(f"Oferta {args.job_id} etiquetada como {args.etiqueta}")
        elif args.cmd == "eval":
            print(ev.render_summary(ev.summary(session, active.id)))


if __name__ == "__main__":
    main()
