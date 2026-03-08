"""Initial schema with all tables and TimescaleDB hypertable.

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-03-02 00:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all tables in correct FK dependency order."""
    
    # Users table (no FK dependencies)
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('role', sa.Enum('analyst', 'risk_manager', 'cfo', 'admin', name='userrole'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    
    # Platform config table (depends on users)
    op.create_table(
        'platform_config',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('key', sa.String(100), nullable=False, unique=True, index=True),
        sa.Column('value', postgresql.JSONB, nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('updated_by_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['updated_by_id'], ['users.id'], ondelete='RESTRICT'),
        sa.CheckConstraint(
            "key IN ('hr_cap', 'collateral_limit', 'ifrs9_r2_min', 'mape_target', "
            "'var_reduction_target', 'max_coverage_ratio', 'pipeline_timeout')",
            name='valid_config_keys'
        ),
    )
    
    # Price ticks table (TimescaleDB hypertable, no FK dependencies)
    # TimescaleDB requires partitioning column 'time' in primary/unique key
    op.create_table(
        'price_ticks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('time', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('jet_fuel_spot', sa.Numeric(15, 2), nullable=False),
        sa.Column('heating_oil_futures', sa.Numeric(15, 2), nullable=False),
        sa.Column('brent_futures', sa.Numeric(15, 2), nullable=False),
        sa.Column('wti_futures', sa.Numeric(15, 2), nullable=False),
        sa.Column('crack_spread', sa.Numeric(15, 2), nullable=False),
        sa.Column('volatility_index', sa.Numeric(5, 2), nullable=False),
        sa.Column('quality_flag', sa.String(50), nullable=True),
        sa.Column('source', sa.String(50), nullable=False, server_default='API'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('time', 'id'),
        sa.UniqueConstraint('time', 'source', name='unique_tick_time_source'),
        sa.CheckConstraint('jet_fuel_spot > 0', name='positive_jet_fuel'),
        sa.CheckConstraint('heating_oil_futures > 0', name='positive_heating_oil'),
        sa.CheckConstraint('brent_futures > 0', name='positive_brent'),
        sa.CheckConstraint('wti_futures > 0', name='positive_wti'),
    )
    
    # Create index for descending time queries
    op.create_index('idx_price_ticks_time_desc', 'price_ticks', [sa.text('time DESC')])
    
    # Convert price_ticks to TimescaleDB hypertable
    op.execute("SELECT create_hypertable('price_ticks', 'time', if_not_exists => TRUE)")
    
    # Analytics runs table (no FK dependencies)
    op.create_table(
        'analytics_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('run_date', sa.Date(), nullable=False, unique=True, index=True),
        sa.Column('mape', sa.Numeric(5, 2), nullable=False),
        sa.Column('forecast_json', postgresql.JSONB, nullable=False),
        sa.Column('var_results', postgresql.JSONB, nullable=False),
        sa.Column('basis_metrics', postgresql.JSONB, nullable=False),
        sa.Column('optimizer_result', postgresql.JSONB, nullable=False),
        sa.Column('model_versions', postgresql.JSONB, nullable=False),
        sa.Column('duration_seconds', sa.Numeric(10, 2), nullable=False),
        sa.Column('status', sa.Enum('RUNNING', 'COMPLETED', 'FAILED', name='analyticsrunstatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('mape >= 0 AND mape <= 100', name='valid_mape'),
        sa.CheckConstraint('duration_seconds > 0', name='positive_duration'),
    )
    
    # Hedge recommendations table (depends on analytics_runs)
    op.create_table(
        'hedge_recommendations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('optimal_hr', sa.Numeric(5, 4), nullable=False),
        sa.Column('instrument_mix', postgresql.JSONB, nullable=False),
        sa.Column('proxy_weights', postgresql.JSONB, nullable=False),
        sa.Column('var_hedged', sa.Numeric(15, 2), nullable=False),
        sa.Column('var_unhedged', sa.Numeric(15, 2), nullable=False),
        sa.Column('var_reduction_pct', sa.Numeric(5, 2), nullable=False),
        sa.Column('collateral_usd', sa.Numeric(15, 2), nullable=False),
        sa.Column('agent_outputs', postgresql.JSONB, nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'APPROVED', 'REJECTED', 'DEFERRED', 'EXPIRED', 'CONSTRAINT_VIOLATED', name='recommendationstatus'), nullable=False, server_default='PENDING'),
        sa.Column('sequence_number', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('escalation_flag', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['analytics_runs.id'], ondelete='RESTRICT'),
        sa.CheckConstraint('optimal_hr >= 0 AND optimal_hr <= 0.80', name='hr_within_cap'),
        sa.CheckConstraint('var_reduction_pct >= 0 AND var_reduction_pct <= 100', name='valid_var_reduction'),
        sa.CheckConstraint('collateral_usd >= 0', name='non_negative_collateral'),
    )
    
    # Create composite index for recommendations
    op.create_index('idx_recommendations_status_created', 'hedge_recommendations', ['status', 'created_at'])
    
    # Approvals table (depends on hedge_recommendations and users)
    op.create_table(
        'approvals',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('recommendation_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('approver_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('decision', sa.Enum('APPROVE', 'REJECT', 'DEFER', name='decisiontype'), nullable=False),
        sa.Column('response_lag_minutes', sa.Numeric(10, 2), nullable=False),
        sa.Column('override_reason', sa.Text(), nullable=True),
        sa.Column('ip_address', postgresql.INET(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['recommendation_id'], ['hedge_recommendations.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['approver_id'], ['users.id'], ondelete='RESTRICT'),
        sa.CheckConstraint('response_lag_minutes >= 0', name='non_negative_response_lag'),
    )
    
    # Hedge positions table (depends on hedge_recommendations)
    op.create_table(
        'hedge_positions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('recommendation_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('instrument_type', sa.Enum('FUTURES', 'OPTIONS', 'COLLAR', 'SWAP', name='instrumenttype'), nullable=False),
        sa.Column('proxy', sa.String(50), nullable=False),
        sa.Column('notional_usd', sa.Numeric(15, 2), nullable=False),
        sa.Column('hedge_ratio', sa.Numeric(5, 4), nullable=False),
        sa.Column('entry_price', sa.Numeric(15, 2), nullable=False),
        sa.Column('expiry_date', sa.Date(), nullable=False),
        sa.Column('collateral_usd', sa.Numeric(15, 2), nullable=False),
        sa.Column('ifrs9_r2', sa.Numeric(5, 4), nullable=False),
        sa.Column('status', sa.Enum('OPEN', 'CLOSED', 'EXPIRED', name='positionstatus'), nullable=False, server_default='OPEN'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['recommendation_id'], ['hedge_recommendations.id'], ondelete='RESTRICT'),
        sa.CheckConstraint('notional_usd > 0', name='positive_notional'),
        sa.CheckConstraint('hedge_ratio >= 0 AND hedge_ratio <= 1.0', name='valid_hedge_ratio'),
        sa.CheckConstraint('entry_price > 0', name='positive_entry_price'),
        sa.CheckConstraint('collateral_usd >= 0', name='non_negative_collateral'),
        sa.CheckConstraint('ifrs9_r2 >= 0 AND ifrs9_r2 <= 1.0', name='valid_r2'),
    )
    
    # Create composite index for positions
    op.create_index('idx_positions_status_expiry', 'hedge_positions', ['status', 'expiry_date'])
    
    # Audit logs table (depends on users)
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('action', sa.String(100), nullable=False, index=True),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('before_state', postgresql.JSONB, nullable=True),
        sa.Column('after_state', postgresql.JSONB, nullable=False),
        sa.Column('ip_address', postgresql.INET(), nullable=False),
        sa.Column('user_agent', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='RESTRICT'),
    )
    
    # Create indexes for audit logs
    op.create_index('idx_audit_created_at_desc', 'audit_logs', [sa.text('created_at DESC')])
    op.create_index('idx_audit_action_created', 'audit_logs', ['action', 'created_at'])


def downgrade() -> None:
    """Drop all tables in reverse FK dependency order."""
    
    # Drop tables with FK dependencies first
    op.drop_table('audit_logs')
    op.drop_table('hedge_positions')
    op.drop_table('approvals')
    op.drop_table('hedge_recommendations')
    op.drop_table('analytics_runs')
    op.drop_table('price_ticks')
    op.drop_table('platform_config')
    op.drop_table('users')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS positionstatus')
    op.execute('DROP TYPE IF EXISTS instrumenttype')
    op.execute('DROP TYPE IF EXISTS decisiontype')
    op.execute('DROP TYPE IF EXISTS recommendationstatus')
    op.execute('DROP TYPE IF EXISTS analyticsrunstatus')
    op.execute('DROP TYPE IF EXISTS userrole')
