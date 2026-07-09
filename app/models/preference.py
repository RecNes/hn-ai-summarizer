"""Database models for user preferences."""

from typing import Optional

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserPreference(Base):
    """Database model for user preferences."""

    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    highlight_keywords: Mapped[Optional[str]] = mapped_column(Text)
    blocklist_keywords: Mapped[Optional[str]] = mapped_column(Text)

    # Language preferences
    ui_language: Mapped[str] = mapped_column(String(10), default="en")
    translation_language: Mapped[str] = mapped_column(String(10), default="en")
