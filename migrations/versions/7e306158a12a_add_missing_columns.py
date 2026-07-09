"""add_missing_columns

Revision ID: 7e306158a12a
Revises: 20230501_initial
Create Date: 2026-07-09 15:13:23.030540

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7e306158a12a'
down_revision = '20230501_initial'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE settings ADD COLUMN IF NOT EXISTS ai_provider VARCHAR")
    op.execute("ALTER TABLE settings ADD COLUMN IF NOT EXISTS ai_model VARCHAR")
    op.execute("ALTER TABLE settings ADD COLUMN IF NOT EXISTS ai_provider_config TEXT")


def downgrade():
    op.execute("ALTER TABLE settings DROP COLUMN IF EXISTS ai_provider_config")
    op.execute("ALTER TABLE settings DROP COLUMN IF EXISTS ai_model")
    op.execute("ALTER TABLE settings DROP COLUMN IF EXISTS ai_provider")
