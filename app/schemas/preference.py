"""Schemas for user preferences."""

from typing import Optional

from pydantic import BaseModel


class PreferenceBase(BaseModel):
    """Base schema for user preferences."""
    highlight_keywords: Optional[str] = None
    blocklist_keywords: Optional[str] = None


class PreferenceUpdate(PreferenceBase):
    """Schema for updating user preferences."""
    pass


class PreferenceResponse(PreferenceBase):
    """Schema for responding with user preferences."""
    id: int

    class Config:
        """Pydantic configuration to work with ORM objects."""
        from_attributes = True
