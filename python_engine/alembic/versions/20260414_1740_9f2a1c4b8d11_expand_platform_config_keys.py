"""expand_platform_config_keys

Revision ID: 9f2a1c4b8d11
Revises: 6b35deb365c7
Create Date: 2026-04-14 17:40:00.000000+00:00
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "9f2a1c4b8d11"
down_revision = "6b35deb365c7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("valid_config_keys", "platform_config", type_="check")
    op.create_check_constraint(
        "valid_config_keys",
        "platform_config",
        "key IN ('hr_cap', 'collateral_limit', 'ifrs9_r2_min', 'mape_target', "
        "'var_reduction_target', 'max_coverage_ratio', 'pipeline_timeout', "
        "'monthly_consumption_bbl', 'instrument_preference', 'hr_band_min')",
    )


def downgrade() -> None:
    op.drop_constraint("valid_config_keys", "platform_config", type_="check")
    op.create_check_constraint(
        "valid_config_keys",
        "platform_config",
        "key IN ('hr_cap', 'collateral_limit', 'ifrs9_r2_min', 'mape_target', "
        "'var_reduction_target', 'max_coverage_ratio', 'pipeline_timeout')",
    )
