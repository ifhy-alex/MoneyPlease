"""matching: profiles, matches, match_runs, job_labels e índice HNSW

Revision ID: 0002
Revises: 0001
"""
import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "profiles",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("version", sa.Integer, nullable=False, unique=True),
        sa.Column("cv_texto", sa.Text, nullable=False, server_default=""),
        sa.Column("perfil_json", JSONB, nullable=False),
        sa.Column("embedding", Vector(384), nullable=False),
        sa.Column("creado_en", TS, nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "matches",
        sa.Column("profile_id", sa.Integer, sa.ForeignKey("profiles.id"), primary_key=True),
        sa.Column("job_id", sa.Integer, sa.ForeignKey("jobs.id"), primary_key=True),
        sa.Column("score", sa.Integer, nullable=False),
        sa.Column("fit", sa.Text, nullable=False),
        sa.Column("fortalezas", JSONB, nullable=False),
        sa.Column("brechas", JSONB, nullable=False),
        sa.Column("resumen", sa.Text, nullable=False),
        sa.Column("modelo", sa.Text, nullable=False),
        sa.Column("evaluado_en", TS, nullable=False),
    )
    op.create_index("ix_matches_profile_score", "matches", ["profile_id", sa.text("score DESC")])
    op.create_table(
        "match_runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("profile_id", sa.Integer, sa.ForeignKey("profiles.id"), nullable=False),
        sa.Column("iniciado_en", TS, nullable=False),
        sa.Column("terminado_en", TS),
        sa.Column("embebidas", sa.Integer, nullable=False, server_default="0"),
        sa.Column("candidatas", sa.Integer, nullable=False, server_default="0"),
        sa.Column("evaluadas", sa.Integer, nullable=False, server_default="0"),
        sa.Column("fallidas", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cuota_agotada", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("error", sa.Text),
    )
    op.create_table(
        "job_labels",
        sa.Column("job_id", sa.Integer, sa.ForeignKey("jobs.id"), primary_key=True),
        sa.Column("etiqueta", sa.Text, nullable=False),
        sa.Column("creado_en", TS, nullable=False, server_default=sa.func.now()),
    )
    op.execute("CREATE INDEX ix_jobs_embedding_hnsw ON jobs USING hnsw (embedding vector_cosine_ops)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_jobs_embedding_hnsw")
    op.drop_table("job_labels")
    op.drop_table("match_runs")
    op.drop_table("matches")
    op.drop_table("profiles")
