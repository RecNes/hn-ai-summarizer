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
    op.create_table('settings',
        sa.Column('id', sa.Integer(), nullable=False),
        # AI Provider settings
        sa.Column('ai_provider', sa.String(), nullable=True),
        sa.Column('ai_model', sa.String(), nullable=True),
        sa.Column('ai_provider_config', sa.Text(), nullable=True),
        # Legacy Ollama fields
        sa.Column('ollama_api_url', sa.String(), nullable=True),
        sa.Column('ollama_model', sa.String(), nullable=True),
        # Schedule
        sa.Column('cron_schedule', sa.String(), nullable=True),
        sa.Column('min_score', sa.Integer(), nullable=True),
        sa.Column('retention_days', sa.Integer(), nullable=True),
        sa.Column('scheduled_hour', sa.Integer(), nullable=True),
        sa.Column('scheduled_minute', sa.Integer(), nullable=True),
        sa.Column('scheduled_days', sa.String(), nullable=True),
        # SMTP
        sa.Column('smtp_host', sa.String(), nullable=True),
        sa.Column('smtp_port', sa.Integer(), nullable=True),
        sa.Column('smtp_username', sa.String(), nullable=True),
        sa.Column('smtp_password', sa.String(), nullable=True),
        sa.Column('smtp_from', sa.String(), nullable=True),
        # Display
        sa.Column('display_font_family', sa.String(), nullable=True),
        sa.Column('display_font_size', sa.String(), nullable=True),
        sa.Column('display_contrast', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_settings_id'), 'settings', ['id'], unique=False)

    op.create_table('user_preferences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('highlight_keywords', sa.Text(), nullable=True),
        sa.Column('blocklist_keywords', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_preferences_id'), 'user_preferences', ['id'], unique=False)

    op.create_table('stories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('hacker_news_id', sa.String(), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('title_tr', sa.String(), nullable=True),
        sa.Column('url', sa.String(), nullable=True),
        sa.Column('score', sa.Integer(), nullable=True),
        sa.Column('author', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('content_tr', sa.Text(), nullable=True),
        sa.Column('comments_summary', sa.Text(), nullable=True),
        sa.Column('image_url', sa.String(), nullable=True),
        sa.Column('is_highlighted', sa.Boolean(), nullable=True),
        sa.Column('is_dimmed', sa.Boolean(), nullable=True),
        sa.Column('is_blocked', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_stories_hacker_news_id'), 'stories', ['hacker_news_id'], unique=True)
    op.create_index(op.f('ix_stories_id'), 'stories', ['id'], unique=False)

    op.create_table('negative_feedback',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('story_id', sa.Integer(), nullable=True),
        sa.Column('keywords', sa.Text(), nullable=True),
        sa.Column('embedding', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['story_id'], ['stories.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_negative_feedback_id'), 'negative_feedback', ['id'], unique=False)


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