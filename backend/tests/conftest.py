import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="session")
def db_url():
    url = os.environ.get("TEST_DATABASE_URL")
    container = None
    if not url:
        from testcontainers.community.postgres import PostgresContainer

        container = PostgresContainer("pgvector/pgvector:pg16", driver="psycopg")
        container.start()
        url = container.get_connection_url()
    cfg = Config(os.path.join(BACKEND, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BACKEND, "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")
    yield url
    if container:
        container.stop()


@pytest.fixture(scope="session")
def session_factory(db_url):
    engine = create_engine(db_url)
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()


@pytest.fixture
def session(session_factory):
    s = session_factory()
    yield s
    s.rollback()
    s.execute(text("TRUNCATE applications, job_labels, match_failures, matches, match_runs, profiles, ingest_runs, jobs, sources RESTART IDENTITY CASCADE"))
    s.commit()
    s.close()
