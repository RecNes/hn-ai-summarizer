"""Pydantic schemas for application settings."""

from typing import Any

from pydantic import BaseModel


class SettingBase(BaseModel):
    """Base schema for application settings.

    NOTE: API keys are NEVER stored in DB or exposed to frontend.
    They are only read from .env file on the backend.
    """

    # AI Provider settings
    ai_provider: str | None = None
    ai_model: str | None = None
    ai_provider_config: str | None = None  # JSON string for configurable providers

    # Legacy Ollama fields
    ollama_api_url: str | None = None
    ollama_model: str | None = None

    # Schedule settings
    cron_schedule: str | None = None
    min_score: int | None = None
    retention_days: int | None = None
    scheduled_hour: int | None = None
    scheduled_minute: int | None = None
    scheduled_days: str | None = None

    # Telegram settings
    telegram_chat_id: str | None = None
    telegram_enabled: bool = False

    # Display settings
    display_font_family: str | None = None
    display_font_size: str | None = None
    display_contrast: str | None = None


class SettingUpdate(SettingBase):
    """Schema for updating application settings."""



class SettingResponse(SettingBase):
    """Schema for responding with application settings."""

    id: int
    available_providers: list[dict[str, Any]] = []
    available_languages: list[dict[str, Any]] = []
    telegram_available: bool = False
    timezone: str = "UTC"
    timezone_configured: bool = False

    class Config:
        """Pydantic configuration to work with ORM objects."""

        from_attributes = True
