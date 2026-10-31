"""dashboard: applications, matches.ejemplos_hash y extensión unaccent

Revision ID: 0004
Revises: 0003
"""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.add_column("matches", sa.Column("ejemplos_hash", sa.Text))
    op.create_table(
        "applications",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("job_id", sa.Integer, sa.ForeignKey("jobs.id"), nullable=False, unique=True),
        sa.Column("estado", sa.Text, nullable=False),
        sa.Column("notas", sa.Text, nullable=False, server_default=""),
        sa.Column("fecha_aplicacion", sa.Date),
        sa.Column("siguiente_paso", sa.Text, nullable=False, server_default=""),
        sa.Column("estado_desde", TS, nullable=False),
        sa.Column("recordatorio_hasta", TS),
        sa.Column("creado_en", TS, nullable=False),
        sa.Column("actualizado_en", TS, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("applications")
    op.drop_column("matches", "ejemplos_hash")
