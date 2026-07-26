"""Database models for stories and negative feedback."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.feedback import NegativeFeedback


class Story(Base):
    """Database model for stories."""

    __tablename__ = "stories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    hacker_news_id: Mapped[str | None] = mapped_column(
        String, unique=True, index=True
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    title_tr: Mapped[str | None] = mapped_column(String)
    url: Mapped[str | None] = mapped_column(String)
    score: Mapped[int | None] = mapped_column(Integer)
    author: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    hn_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, onupdate=lambda: datetime.now(UTC)
    )
    content: Mapped[str | None] = mapped_column(Text)
    content_tr: Mapped[str | None] = mapped_column(Text)
    comments_summary: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String)
    is_highlighted: Mapped[bool | None] = mapped_column(Boolean, default=False)
    is_dimmed: Mapped[bool | None] = mapped_column(Boolean, default=False)
    is_blocked: Mapped[bool | None] = mapped_column(Boolean, default=False)
    is_translated: Mapped[bool | None] = mapped_column(Boolean, default=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    negative_feedback: Mapped[list["NegativeFeedback"]] = relationship(
        "NegativeFeedback", back_populates="story"
    )
