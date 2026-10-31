"""match_failures: ofertas cuya evaluación falla, para dejar de reintentarlas

Revision ID: 0003
Revises: 0002
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "match_failures",
        sa.Column("profile_id", sa.Integer, sa.ForeignKey("profiles.id"), primary_key=True),
        sa.Column("job_id", sa.Integer, sa.ForeignKey("jobs.id"), primary_key=True),
        sa.Column("intentos", sa.Integer, nullable=False, server_default="0"),
        sa.Column("ultimo_error", sa.Text),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("match_failures")
