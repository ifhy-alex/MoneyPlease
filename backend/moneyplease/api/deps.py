from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session

from moneyplease.config import Settings


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_session(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        yield session


def get_llm(request: Request):
    """Proveedor de LLM, o None si no hay key o el dashboard corre en modo demo."""
    from moneyplease.matching.factory import build_llm

    settings: Settings = request.app.state.settings
    if settings.demo_mode or not settings.gemini_api_key:
        return None
    return build_llm(settings)


def get_embedder():
    from moneyplease.matching.factory import build_embedder

    return build_embedder()
