"""Database model for registered Android/iOS devices."""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Device(Base):
    """Database model for paired mobile devices."""

    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_name: Mapped[str] = mapped_column(String, nullable=False)
    device_id: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    pairing_code: Mapped[str | None] = mapped_column(String, nullable=True)
    auth_token: Mapped[str | None] = mapped_column(String, nullable=True)
    is_paired: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_connected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )