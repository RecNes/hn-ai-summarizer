"""Database model for application settings."""

from typing import Optional

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Setting(Base):
    """Database model for application settings."""

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # AI Provider settings (selected provider + model stored in DB)
    ai_provider: Mapped[Optional[str]] = mapped_column(String, default=None)
    ai_model: Mapped[Optional[str]] = mapped_column(String, default=None)
    ai_provider_config: Mapped[Optional[str]] = mapped_column(Text, default=None)

    # Legacy fields - kept for backward compatibility during migration
    ollama_api_url: Mapped[Optional[str]] = mapped_column(
        String, default="http://host.docker.internal:11434"
    )
    ollama_model: Mapped[Optional[str]] = mapped_column(String, default="llama2")

    # Schedule settings
    cron_schedule: Mapped[Optional[str]] = mapped_column(String, default="0 9 * * *")
    min_score: Mapped[Optional[int]] = mapped_column(Integer, default=100)
    retention_days: Mapped[Optional[int]] = mapped_column(Integer, default=30)
    scheduled_hour: Mapped[Optional[int]] = mapped_column(Integer, default=9)
    scheduled_minute: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    scheduled_days: Mapped[Optional[str]] = mapped_column(String, default="1,2,3,4,5")

    # SMTP settings
    smtp_host: Mapped[Optional[str]] = mapped_column(String)
    smtp_port: Mapped[Optional[int]] = mapped_column(Integer)
    smtp_username: Mapped[Optional[str]] = mapped_column(String)
    smtp_password: Mapped[Optional[str]] = mapped_column(String)
    smtp_from: Mapped[Optional[str]] = mapped_column(String)

    # Display settings
    display_font_family: Mapped[Optional[str]] = mapped_column(
        String, default="Atkinson Hyperlegible"
    )
    display_font_size: Mapped[Optional[str]] = mapped_column(String, default="medium")
    display_contrast: Mapped[Optional[str]] = mapped_column(String, default="light")
