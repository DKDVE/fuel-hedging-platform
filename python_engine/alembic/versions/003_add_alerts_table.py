"""Add alerts table.

Revision ID: 003_add_alerts
Revises: 002_add_backtest_runs
Create Date: 2026-03-07

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "003_add_alerts"
down_revision = "002_add_backtest_runs"
branch_labels = None
depends_on = None

# Create enums only if they don't exist (idempotent for partial migration recovery)
CREATE_ALERTTYPE = """
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'alerttype') THEN
        CREATE TYPE alerttype AS ENUM (
            'VAR_APPROACHING_LIMIT', 'COLLATERAL_HIGH', 'MAPE_DEGRADED', 'RECOMMENDATION_SLA',
            'PRICE_SPIKE', 'PIPELINE_FAILED', 'IFRS9_WARNING', 'HR_APPROACHING_CAP'
        );
    END IF;
END $$;
"""
CREATE_ALERTSEVERITY = """
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'alertseverity') THEN
        CREATE TYPE alertseverity AS ENUM ('INFO', 'WARNING', 'CRITICAL');
    END IF;
END $$;
"""

alerttype_enum = postgresql.ENUM(
    "VAR_APPROACHING_LIMIT", "COLLATERAL_HIGH", "MAPE_DEGRADED", "RECOMMENDATION_SLA",
    "PRICE_SPIKE", "PIPELINE_FAILED", "IFRS9_WARNING", "HR_APPROACHING_CAP",
    name="alerttype",
    create_type=False,  # We create via raw SQL above
)
alertseverity_enum = postgresql.ENUM("INFO", "WARNING", "CRITICAL", name="alertseverity", create_type=False)


def upgrade() -> None:
    op.execute(sa.text(CREATE_ALERTTYPE))
    op.execute(sa.text(CREATE_ALERTSEVERITY))

    conn = op.get_bind()
    if not conn.execute(sa.text(
        "SELECT 1 FROM information_schema.tables WHERE table_name = 'alerts'"
    )).scalar():
        op.create_table(
            "alerts",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("alert_type", alerttype_enum, nullable=False, index=True),
            sa.Column("severity", alertseverity_enum, nullable=False, index=True),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("metric_value", sa.Float(), nullable=True),
            sa.Column("threshold_value", sa.Float(), nullable=True),
            sa.Column("is_acknowledged", sa.Boolean(), server_default=sa.false(), nullable=False, index=True),
            sa.Column("acknowledged_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("dedup_key", sa.String(100), nullable=True, index=True),
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
        op.create_index("idx_alerts_created_at_desc", "alerts", ["created_at"], postgresql_ops={"created_at": "DESC"})


def downgrade() -> None:
    op.drop_index("idx_alerts_created_at_desc", table_name="alerts")
    op.drop_table("alerts")
    alerttype_enum.drop(op.get_bind(), checkfirst=True)
    alertseverity_enum.drop(op.get_bind(), checkfirst=True)
