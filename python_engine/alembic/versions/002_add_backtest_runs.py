"""Add backtest_runs table.

Revision ID: 002_add_backtest_runs
Revises: 001_initial_schema
Create Date: 2026-03-07

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002_add_backtest_runs"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "backtest_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("notional_usd", sa.Numeric(15, 2), nullable=False),
        sa.Column("weekly_results", postgresql.JSONB, nullable=False),
        sa.Column("summary", postgresql.JSONB, nullable=False),
        sa.Column("dataset_hash", sa.String(64), nullable=False, index=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("backtest_runs")
