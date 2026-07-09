"""Schemas for user preferences."""

from typing import Optional

from pydantic import BaseModel


class PreferenceBase(BaseModel):
    """Base schema for user preferences."""
    highlight_keywords: Optional[str] = None
    blocklist_keywords: Optional[str] = None
    ui_language: Optional[str] = "en"
    translation_language: Optional[str] = "en"


class PreferenceUpdate(PreferenceBase):
    """Schema for updating user preferences."""
    pass


class PreferenceResponse(PreferenceBase):
    """Schema for responding with user preferences."""
    id: int
    ui_language: str = "en"
    translation_language: str = "en"
    available_languages: list = []  # populated by API

    class Config:
        """Pydantic configuration to work with ORM objects."""
        from_attributes = True
