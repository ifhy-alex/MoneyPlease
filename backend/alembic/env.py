from alembic import context
from sqlalchemy import create_engine, text

from moneyplease.config import get_settings

config = context.config
url = context.get_x_argument(as_dictionary=True).get("url") or config.get_main_option("sqlalchemy.url") \
    or get_settings().database_url

engine = create_engine(url)
with engine.connect() as connection:
    context.configure(connection=connection)
    with context.begin_transaction():
        # web y worker migran al arrancar: el lock hace que uno espere al otro.
        connection.execute(text("SELECT pg_advisory_xact_lock(4242)"))
        context.run_migrations()
engine.dispose()
