"""API routes for activity logs (AI, worker, etc.)."""

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.models.activity_log import AiActivityLog
from app.schemas.activity_log import AiActivityLogResponse

router = APIRouter()


@router.get("/", response_model=List[AiActivityLogResponse])
async def get_activity(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    event_category: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get recent activity logs with pagination and optional event_category filter."""
    query = select(AiActivityLog).order_by(AiActivityLog.created_at.desc())
    if event_category:
        query = query.where(AiActivityLog.event_category == event_category)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    logs = result.scalars().all()
    return logs