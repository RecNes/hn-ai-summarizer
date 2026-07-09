"""Add is_translated column to stories, migrate existing data

- Adds is_translated boolean column (default False)
- For existing records: removes [TR] prefix from title_tr (sets to original title)
- Sets is_translated based on content quality checks

Revision ID: 20260709_add_is_translated
Revises: 20230501_initial
Create Date: 2026-07-09

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260709_add_is_translated'
down_revision = '7e306158a12a'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add is_translated column
    op.execute("""
        ALTER TABLE stories
        ADD COLUMN is_translated BOOLEAN NOT NULL DEFAULT FALSE
    """)

    # 2. Migrate existing data:
    #    - Remove [TR] prefix from title_tr (restore original title)
    #    - Set is_translated based on actual content quality
    op.execute("""
        UPDATE stories
        SET
            title_tr = CASE
                WHEN title_tr LIKE '[TR]%' THEN title
                ELSE title_tr
            END,
            is_translated = CASE
                WHEN (
                    (title_tr IS NOT NULL AND title_tr NOT LIKE '[TR]%')
                    AND (content_tr IS NOT NULL
                         AND content_tr != ''
                         AND content_tr != 'İçerik özeti mevcut değil.'
                         AND content_tr != 'Özet oluşturulamadı.')
                    AND (comments_summary IS NOT NULL
                         AND comments_summary != ''
                         AND comments_summary != 'Yorum özeti mevcut değil.')
                )
                THEN TRUE
                ELSE FALSE
            END
    """)


def downgrade():
    op.execute("ALTER TABLE stories DROP COLUMN is_translated")