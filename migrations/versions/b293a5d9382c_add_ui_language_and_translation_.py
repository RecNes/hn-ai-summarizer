"""Add ui_language and translation_language to user_preferences

Revision ID: b293a5d9382c
Revises: 20260709_add_is_translated
Create Date: 2026-07-09 20:23:00.285738

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b293a5d9382c'
down_revision = '20260709_add_is_translated'
branch_labels = None
depends_on = None


def upgrade():
    # Add language columns to user_preferences
    op.add_column(
        'user_preferences',
        sa.Column('ui_language', sa.String(length=10), nullable=False, server_default='en')
    )
    op.add_column(
        'user_preferences',
        sa.Column('translation_language', sa.String(length=10), nullable=False, server_default='en')
    )


def downgrade():
    op.drop_column('user_preferences', 'translation_language')
    op.drop_column('user_preferences', 'ui_language')