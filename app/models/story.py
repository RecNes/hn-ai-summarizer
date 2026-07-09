"""Database models for stories and negative feedback."""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Story(Base):
    """Database model for stories."""

    __tablename__ = "stories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    hacker_news_id: Mapped[Optional[str]] = mapped_column(
        String, unique=True, index=True
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    title_tr: Mapped[Optional[str]] = mapped_column(String)
    url: Mapped[Optional[str]] = mapped_column(String)
    score: Mapped[Optional[int]] = mapped_column(Integer)
    author: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=None, onupdate=lambda: datetime.now(timezone.utc)
    )
    content: Mapped[Optional[str]] = mapped_column(Text)
    content_tr: Mapped[Optional[str]] = mapped_column(Text)
    comments_summary: Mapped[Optional[str]] = mapped_column(Text)
    image_url: Mapped[Optional[str]] = mapped_column(String)
    is_highlighted: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    is_dimmed: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    is_blocked: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    is_translated: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)

    negative_feedback: Mapped[List["NegativeFeedback"]] = relationship(
        "NegativeFeedback", back_populates="story"
    )
