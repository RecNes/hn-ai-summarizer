"""Database models for negative feedback on stories."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class NegativeFeedback(Base):
    """Database model for negative feedback on stories."""

    __tablename__ = "negative_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    story_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("stories.id"))
    keywords: Mapped[Optional[str]] = mapped_column(Text)
    embedding: Mapped[Optional[str]] = mapped_column(Text)

    story: Mapped[Optional["Story"]] = relationship(
        "Story", back_populates="negative_feedback"
    )
