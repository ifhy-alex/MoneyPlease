from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from moneyplease.config import get_settings


def make_engine(url: str | None = None) -> Engine:
    return create_engine(url or get_settings().database_url)


def make_session(url: str | None = None) -> sessionmaker[Session]:
    return sessionmaker(make_engine(url), expire_on_commit=False)
