"""Pydantic schemas for AI activity and worker event logs."""

from datetime import datetime

from pydantic import BaseModel


class AiActivityLogResponse(BaseModel):
    """Schema for responding with AI activity log data."""
    id: int
    story_id: int | None = None
    story_title: str | None = None
    event_type: str
    provider: str
    model: str
    status: str
    error_message: str | None = None
    duration_ms: float | None = None
    created_at: datetime

    # ── Worker event fields ──────────────────────────────────────
    event_category: str | None = None
    worker_event_type: str | None = None
    worker_status: str | None = None
    worker_phase: str | None = None
    error_code: str | None = None
    error_summary: str | None = None

    class Config:
        """Pydantic configuration to work with ORM objects."""
        from_attributes = True
