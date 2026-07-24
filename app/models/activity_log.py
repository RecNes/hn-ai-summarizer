"""Database model for AI activity and worker event logging."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AiActivityLog(Base):
    """Log entry for AI calls and worker processing events.

    New fields (migration):
    - event_category: "ai_call" | "worker"
    - worker_event_type: "story_new" | "story_reprocess" | "worker_triggered"
    - worker_status: "processing" | "success" | "error"
    - worker_phase: "title" | "content" | "comments"
    - error_code: machine-readable error code
    - error_summary: human-readable short error description
    """

    __tablename__ = "ai_activity_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    story_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    story_title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    event_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # ── Worker event fields ──────────────────────────────────────
    event_category: Mapped[str | None] = mapped_column(
        String(16), nullable=True, index=True
    )
    worker_event_type: Mapped[str | None] = mapped_column(
        String(32), nullable=True, index=True
    )
    worker_status: Mapped[str | None] = mapped_column(
        String(16), nullable=True
    )
    worker_phase: Mapped[str | None] = mapped_column(
        String(16), nullable=True
    )
    error_code: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    error_summary: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )
