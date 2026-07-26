"""Database model for application settings."""


from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Setting(Base):
    """Database model for application settings."""

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # AI Provider settings (selected provider + model stored in DB)
    ai_provider: Mapped[str | None] = mapped_column(String, default=None)
    ai_model: Mapped[str | None] = mapped_column(String, default=None)
    ai_provider_config: Mapped[str | None] = mapped_column(Text, default=None)

    # Legacy fields - kept for backward compatibility during migration
    ollama_api_url: Mapped[str | None] = mapped_column(
        String, default="http://host.docker.internal:11434"
    )
    ollama_model: Mapped[str | None] = mapped_column(String, default="llama2")

    # Schedule settings
    cron_schedule: Mapped[str | None] = mapped_column(String, default="0 9 * * *")
    min_score: Mapped[int | None] = mapped_column(Integer, default=100)
    retention_days: Mapped[int | None] = mapped_column(Integer, default=30)
    scheduled_hour: Mapped[int | None] = mapped_column(Integer, default=9)
    scheduled_minute: Mapped[int | None] = mapped_column(Integer, default=0)
    scheduled_days: Mapped[str | None] = mapped_column(String, default="1,2,3,4,5")

    # Telegram settings
    telegram_chat_id: Mapped[str | None] = mapped_column(String, default=None)
    telegram_enabled: Mapped[bool | None] = mapped_column(Boolean, default=False)

    # Display settings
    display_font_family: Mapped[str | None] = mapped_column(
        String, default="Atkinson Hyperlegible"
    )
    display_font_size: Mapped[str | None] = mapped_column(String, default="medium")
    display_contrast: Mapped[str | None] = mapped_column(String, default="light")
