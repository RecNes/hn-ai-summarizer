"""API routes for activity logs (AI, worker, etc.)."""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.models.activity_log import AiActivityLog
from app.schemas.activity_log import AiActivityLogResponse

router = APIRouter()


@router.get("/", response_model=List[AiActivityLogResponse])
async def get_activity(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Get recent AI activity logs."""
    result = await db.execute(
        select(AiActivityLog)
        .order_by(AiActivityLog.created_at.desc())
        .limit(limit)
    )
    logs = result.scalars().all()
    return logs