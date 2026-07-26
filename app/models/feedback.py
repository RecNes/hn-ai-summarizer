"""Database models for negative feedback on stories."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.story import Story


class NegativeFeedback(Base):
    """Database model for negative feedback on stories."""

    __tablename__ = "negative_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    story_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("stories.id"))
    keywords: Mapped[str | None] = mapped_column(Text)
    embedding: Mapped[str | None] = mapped_column(Text)

    story: Mapped[Story | None] = relationship(
        "Story", back_populates="negative_feedback"
    )
