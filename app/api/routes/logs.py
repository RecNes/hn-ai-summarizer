"""API routes for worker log streaming and browsing."""

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.models.activity_log import AiActivityLog
from app.schemas.activity_log import AiActivityLogResponse

logger = logging.getLogger(__name__)

router = APIRouter()

REDIS_WORKER_LOG_CHANNEL = "hn_reader:worker_log"
REDIS_WORKER_LOG_KEY = "hn_reader:worker_logs:recent"


async def _get_redis():
    """Create a redis asyncio connection."""
    from redis.asyncio import Redis
    from app.core.config import settings

    redis_url = settings.REDIS_CONNECTION_URL or "redis://localhost:6379/0"
    return Redis.from_url(redis_url, decode_responses=True)


@router.get("/recent")
async def get_recent_logs():
    """Get the last 20 worker log entries from Redis.
    
    Returns raw dict list (no Pydantic validation needed since
    Redis stores pre-serialized log entries from the worker).
    """
    r = None
    try:
        r = await _get_redis()
        raw_list = await r.lrange(REDIS_WORKER_LOG_KEY, 0, 19)
        logs = []
        for raw in raw_list:
            try:
                log = json.loads(raw)
                logs.append(log)
            except (json.JSONDecodeError, TypeError):
                pass
        return logs[::-1]  # oldest first (Redis list is newest-first)
    except Exception as e:
        logger.error("[Logs] Failed to read recent logs from Redis: %s", e)
        return []
    finally:
        if r:
            await r.close()


@router.get("/", response_model=list[AiActivityLogResponse])
async def get_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    event_category: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated log entries from the database."""
    try:
        query = select(AiActivityLog).order_by(AiActivityLog.created_at.desc())
        if event_category:
            query = query.where(AiActivityLog.event_category == event_category)
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        logs = result.scalars().all()
        return logs
    except Exception as e:
        logger.error("[Logs] Failed to fetch logs from DB: %s", e)
        return []


@router.get("/stream")
async def log_stream(request: Request):
    """SSE endpoint: GET /api/logs/stream
    
    Subscribes to Redis Pub/Sub channel `hn_reader:worker_log`
    and yields worker log entries as they arrive.
    """
    return StreamingResponse(
        _log_event_generator(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _log_event_generator(request: Request):
    """SSE generator: subscribe to Redis Pub/Sub, forward worker log events."""
    r = None
    pubsub = None

    try:
        r = await _get_redis()
        pubsub = r.pubsub()
        await pubsub.subscribe(REDIS_WORKER_LOG_CHANNEL)

        yield "event: connected\ndata: {}\n\n"

        async for message in pubsub.listen():
            if await request.is_disconnected():
                break
            if message["type"] == "message":
                data = message.get("data", "")
                if isinstance(data, bytes):
                    data = data.decode()
                yield f"event: log_entry\ndata: {data}\n\n"
    except Exception as e:
        logger.error("[SSE/Logs] Redis unavailable, using keepalive only: %s", e)
        while not await request.is_disconnected():
            yield ": keepalive\n\n"
            await asyncio.sleep(30)
    finally:
        if pubsub:
            try:
                await pubsub.unsubscribe(REDIS_WORKER_LOG_CHANNEL)
                await pubsub.close()
            except Exception:
                pass
        if r:
            await r.close()