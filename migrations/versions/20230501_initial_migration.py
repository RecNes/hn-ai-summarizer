"""Initial migration

Revision ID: 20230501_initial
Revises: 
Create Date: 2023-05-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20230501_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id SERIAL NOT NULL,
            ai_provider VARCHAR,
            ai_model VARCHAR,
            ai_provider_config TEXT,
            ollama_api_url VARCHAR,
            ollama_model VARCHAR,
            cron_schedule VARCHAR,
            min_score INTEGER,
            retention_days INTEGER,
            scheduled_hour INTEGER,
            scheduled_minute INTEGER,
            scheduled_days VARCHAR,
            smtp_host VARCHAR,
            smtp_port INTEGER,
            smtp_username VARCHAR,
            smtp_password VARCHAR,
            smtp_from VARCHAR,
            display_font_family VARCHAR,
            display_font_size VARCHAR,
            display_contrast VARCHAR,
            PRIMARY KEY (id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_settings_id ON settings (id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS user_preferences (
            id SERIAL NOT NULL,
            highlight_keywords TEXT,
            blocklist_keywords TEXT,
            PRIMARY KEY (id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_user_preferences_id ON user_preferences (id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS stories (
            id SERIAL NOT NULL,
            hacker_news_id VARCHAR,
            title VARCHAR NOT NULL,
            title_tr VARCHAR,
            url VARCHAR,
            score INTEGER,
            author VARCHAR,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE,
            content TEXT,
            content_tr TEXT,
            comments_summary TEXT,
            image_url VARCHAR,
            is_highlighted BOOLEAN,
            is_dimmed BOOLEAN,
            is_blocked BOOLEAN,
            PRIMARY KEY (id)
        )
    """)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_stories_hacker_news_id ON stories (hacker_news_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_stories_id ON stories (id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS negative_feedback (
            id SERIAL NOT NULL,
            story_id INTEGER REFERENCES stories(id),
            keywords TEXT,
            embedding TEXT,
            PRIMARY KEY (id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_negative_feedback_id ON negative_feedback (id)")


def downgrade():
    op.drop_index(op.f('ix_negative_feedback_id'), table_name='negative_feedback')
    op.drop_table('negative_feedback')
    op.drop_index(op.f('ix_stories_id'), table_name='stories')
    op.drop_index(op.f('ix_stories_hacker_news_id'), table_name='stories')
    op.drop_table('stories')
    op.drop_index(op.f('ix_user_preferences_id'), table_name='user_preferences')
    op.drop_table('user_preferences')
    op.drop_index(op.f('ix_settings_id'), table_name='settings')
    op.drop_table('settings')