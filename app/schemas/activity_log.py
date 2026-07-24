"""Pydantic schemas for AI activity and worker event logs."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AiActivityLogResponse(BaseModel):
    """Schema for responding with AI activity log data."""
    id: int
    story_id: Optional[int] = None
    story_title: Optional[str] = None
    event_type: str
    provider: str
    model: str
    status: str
    error_message: Optional[str] = None
    duration_ms: Optional[float] = None
    created_at: datetime

    # ── Worker event fields ──────────────────────────────────────
    event_category: Optional[str] = None
    worker_event_type: Optional[str] = None
    worker_status: Optional[str] = None
    worker_phase: Optional[str] = None
    error_code: Optional[str] = None
    error_summary: Optional[str] = None

    class Config:
        """Pydantic configuration to work with ORM objects."""
        from_attributes = True
