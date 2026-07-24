"""Health check endpoints for the HN-AI-Summerizer API."""

import json
import logging

from fastapi import APIRouter, Depends

logger = logging.getLogger(__name__)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db

router = APIRouter()


@router.get("/")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Comprehensive health check"""
    db_status = "unknown"

    try:
        # Check database connection
        await db.execute(select(1))
        db_status = "healthy"
    except SQLAlchemyError as e:
        db_status = f"unhealthy: Database error - {str(e)}"
    except Exception as e:  # pylint: disable=broad-except
        db_status = f"unhealthy: Unexpected error - {str(e)}"

    return {
        "status": "healthy" if db_status == "healthy" else "unhealthy",
        "database": db_status,
        "service": "HN-AI-Summerizer API",
    }


@router.get("/ai-status")
async def ai_health_status():
    """Check if the AI model is currently reachable.

    Returns the health status stored in Redis by the worker.
    Falls back to healthy if Redis is not available or key doesn't exist.
    """
    from redis.asyncio import Redis
    from app.core.config import settings as app_settings

    redis_url = app_settings.REDIS_CONNECTION_URL or "redis://localhost:6379/0"

    try:
        redis = Redis.from_url(redis_url, decode_responses=True)
        await redis.ping()

        raw = await redis.get("hn_reader:ai:health")
        await redis.aclose()

        if raw:
            data = json.loads(raw)
            return {
                "healthy": data.get("healthy", True),
                "timestamp": data.get("timestamp"),
            }

        # No key in Redis yet → assume healthy
        return {"healthy": True, "timestamp": None}

    except Exception as e:
        # Redis unavailable → assume healthy (no false positives)
        logger.warning("[Health] Redis unavailable for ai-status: %s", e)
        return {"healthy": True, "timestamp": None}
