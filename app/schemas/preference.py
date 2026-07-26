"""Schemas for user preferences."""


from pydantic import BaseModel


class PreferenceBase(BaseModel):
    """Base schema for user preferences."""
    highlight_keywords: str | None = None
    blocklist_keywords: str | None = None
    ui_language: str = "en"
    translation_language: str = "en"


class PreferenceUpdate(PreferenceBase):
    """Schema for updating user preferences."""


class PreferenceResponse(PreferenceBase):
    """Schema for responding with user preferences."""
    id: int
    ui_language: str = "en"
    translation_language: str = "en"
    available_languages: list[dict] = []  # populated by API

    class Config:
        """Pydantic configuration to work with ORM objects."""
        from_attributes = True