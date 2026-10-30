"""inicial: sources, jobs, ingest_runs

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("key", sa.Text, nullable=False, unique=True),
        sa.Column("nombre", sa.Text, nullable=False),
        sa.Column("tipo", sa.Text, nullable=False),
        sa.Column("config_json", JSONB, nullable=False, server_default="{}"),
        sa.Column("activa", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("desactivada_motivo", sa.Text),
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source_id", sa.Integer, sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("external_id", sa.Text),
        sa.Column("titulo", sa.Text, nullable=False),
        sa.Column("empresa", sa.Text, nullable=False),
        sa.Column("ubicacion", sa.Text, nullable=False, server_default=""),
        sa.Column("modalidad", sa.Text, nullable=False, server_default="desconocida"),
        sa.Column("provincia", sa.Text),
        sa.Column("pais", sa.Text),
        sa.Column("descripcion", sa.Text, nullable=False, server_default=""),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("publicado_en", TS),
        sa.Column("estado", sa.Text, nullable=False, server_default="active"),
        sa.Column("hash", sa.Text, nullable=False, unique=True),
        sa.Column("raw_json", JSONB, nullable=False),
        sa.Column("embedding", Vector(384)),
        sa.Column("primera_vez_visto", TS, nullable=False, server_default=sa.func.now()),
        sa.Column("ultima_vez_visto", TS, nullable=False, server_default=sa.func.now()),
        sa.Column("corridas_ausente", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_index("ix_jobs_estado_publicado", "jobs", ["estado", "publicado_en"])
    op.create_index("ix_jobs_source_id", "jobs", ["source_id"])
    op.create_table(
        "ingest_runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source_id", sa.Integer, sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("iniciado_en", TS, nullable=False),
        sa.Column("terminado_en", TS),
        sa.Column("ok", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("ofertas_traidas", sa.Integer, nullable=False, server_default="0"),
        sa.Column("ofertas_nuevas", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error", sa.Text),
    )


def downgrade() -> None:
    op.drop_table("ingest_runs")
    op.drop_table("jobs")
    op.drop_table("sources")
