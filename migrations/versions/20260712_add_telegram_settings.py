"""Add telegram_chat_id and telegram_enabled to settings

Revision ID: 20260712_add_telegram_settings
Revises: b293a5d9382c
Create Date: 2026-07-12 12:25:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260712_add_telegram_settings'
down_revision = 'b293a5d9382c'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE settings
        ADD COLUMN telegram_chat_id VARCHAR DEFAULT NULL
    """)
    op.execute("""
        ALTER TABLE settings
        ADD COLUMN telegram_enabled BOOLEAN NOT NULL DEFAULT FALSE
    """)


def downgrade():
    op.execute("""
        ALTER TABLE settings
        DROP COLUMN telegram_enabled
    """)
    op.execute("""
        ALTER TABLE settings
        DROP COLUMN telegram_chat_id
    """)