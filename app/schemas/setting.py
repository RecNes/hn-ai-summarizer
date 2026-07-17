"""Pydantic schemas for application settings."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class SettingBase(BaseModel):
    """Base schema for application settings.

    NOTE: API keys are NEVER stored in DB or exposed to frontend.
    They are only read from .env file on the backend.
    """

    # AI Provider settings
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None
    ai_provider_config: Optional[str] = None  # JSON string for configurable providers

    # Legacy Ollama fields
    ollama_api_url: Optional[str] = None
    ollama_model: Optional[str] = None

    # Schedule settings
    cron_schedule: Optional[str] = None
    min_score: Optional[int] = None
    retention_days: Optional[int] = None
    scheduled_hour: Optional[int] = None
    scheduled_minute: Optional[int] = None
    scheduled_days: Optional[str] = None

    # Telegram settings
    telegram_chat_id: Optional[str] = None
    telegram_enabled: bool = False

    # Display settings
    display_font_family: Optional[str] = None
    display_font_size: Optional[str] = None
    display_contrast: Optional[str] = None


class SettingUpdate(SettingBase):
    """Schema for updating application settings."""

    pass


class SettingResponse(SettingBase):
    """Schema for responding with application settings."""

    id: int
    available_providers: List[Dict[str, Any]] = []
    telegram_available: bool = False

    class Config:
        """Pydantic configuration to work with ORM objects."""

        from_attributes = True
