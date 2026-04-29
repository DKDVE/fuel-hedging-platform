"""make_position_recommendation_id_nullable

Revision ID: 3a2afd9c31af
Revises: 9f2a1c4b8d11
Create Date: 2026-04-29 10:04:03.949455+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3a2afd9c31af'
down_revision = '9f2a1c4b8d11'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        'hedge_positions',
        'recommendation_id',
        existing_type=sa.UUID(),
        nullable=True,
    )
    op.drop_constraint('hedge_positions_recommendation_id_fkey', 'hedge_positions', type_='foreignkey')
    op.create_foreign_key(
        'hedge_positions_recommendation_id_fkey',
        'hedge_positions',
        'hedge_recommendations',
        ['recommendation_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('hedge_positions_recommendation_id_fkey', 'hedge_positions', type_='foreignkey')
    op.create_foreign_key(
        'hedge_positions_recommendation_id_fkey',
        'hedge_positions',
        'hedge_recommendations',
        ['recommendation_id'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.alter_column(
        'hedge_positions',
        'recommendation_id',
        existing_type=sa.UUID(),
        nullable=False,
    )
