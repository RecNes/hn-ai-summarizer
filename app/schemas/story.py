"""Pydantic schemas for stories."""

from datetime import datetime

from pydantic import BaseModel


class StoryBase(BaseModel):
    """Base schema for stories."""
    hacker_news_id: str
    title: str
    title_tr: str | None = None
    url: str | None = None
    score: int
    author: str
    content: str | None = None
    content_tr: str | None = None
    comments_summary: str | None = None
    image_url: str | None = None
    is_highlighted: bool = False
    is_dimmed: bool = False
    is_blocked: bool = False
    is_translated: bool = False
    is_read: bool = False


class StoryCreate(StoryBase):
    """Schema for creating a new story."""


class StoryResponse(StoryBase):
    """Schema for responding with story data."""
    id: int
    created_at: datetime
    hn_created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        """Pydantic configuration to work with ORM objects."""
        from_attributes = True
