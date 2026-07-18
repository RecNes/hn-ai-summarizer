"""Pydantic schemas for AI activity logs."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AiActivityLogResponse(BaseModel):
    """Schema for responding with AI activity log data."""
    id: int
    story_id: Optional[int] = None
    event_type: str
    provider: str
    model: str
    status: str
    error_message: Optional[str] = None
    duration_ms: Optional[float] = None
    created_at: datetime

    class Config:
        """Pydantic configuration to work with ORM objects."""
        from_attributes = True