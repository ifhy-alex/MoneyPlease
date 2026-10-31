from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session, sessionmaker

from moneyplease.api.routes import jobs, profile, top
from moneyplease.config import Settings, get_settings
from moneyplease.db.session import make_session

DEFAULT_STATIC = Path("/app/static")


def create_app(settings: Settings | None = None, session_factory: sessionmaker[Session] | None = None,
               static_dir: Path | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="MoneyPlease")
    app.state.settings = settings
    app.state.session_factory = session_factory or make_session(
        settings.demo_database_url if settings.demo_mode else settings.database_url)
    for module in (top, jobs, profile):
        app.include_router(module.router, prefix="/api")

    @app.api_route("/api/{rest:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
    def api_not_found(rest: str):
        raise HTTPException(404, "Ruta de API inexistente")

    static_dir = static_dir if static_dir is not None else DEFAULT_STATIC
    index = static_dir / "index.html"
    if index.exists():
        if (static_dir / "assets").is_dir():
            app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            # Archivos del build (favicon, fuentes…) o la SPA para cualquier ruta del frontend.
            candidate = (static_dir / path).resolve()
            if path and candidate.is_file() and static_dir.resolve() in candidate.parents:
                return FileResponse(candidate)
            return FileResponse(index)
    return app


app = create_app()
