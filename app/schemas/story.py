"""Pydantic schemas for stories."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class StoryBase(BaseModel):
    """Base schema for stories."""
    hacker_news_id: str
    title: str
    title_tr: Optional[str] = None
    url: Optional[str] = None
    score: int
    author: str
    content: Optional[str] = None
    content_tr: Optional[str] = None
    comments_summary: Optional[str] = None
    image_url: Optional[str] = None
    is_highlighted: bool = False
    is_dimmed: bool = False
    is_blocked: bool = False


class StoryCreate(StoryBase):
    """Schema for creating a new story."""
    pass


class StoryResponse(StoryBase):
    """Schema for responding with story data."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        """Pydantic configuration to work with ORM objects."""
        from_attributes = True
