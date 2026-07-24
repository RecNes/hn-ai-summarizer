"""Redis-based reprocess state management."""

import json
import logging
from typing import Optional

from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)

REDIS_REPROCESS_STATUS_KEY = "hn_reader:reprocess:status"


async def _get_redis() -> Redis:
    """Create a redis asyncio connection."""
    redis_url = settings.REDIS_CONNECTION_URL or "redis://localhost:6379/0"
    return Redis.from_url(redis_url, decode_responses=True)


async def get_reprocess_state() -> dict:
    """Get the current reprocess state from Redis."""
    r = None
    try:
        r = await _get_redis()
        data = await r.get(REDIS_REPROCESS_STATUS_KEY)
        if data:
            return json.loads(data)
        return {"running": False, "current": 0, "total": 0, "percentage": 0, "story_id": None, "cancelled": False}
    except Exception as e:
        logger.error("[ReprocessState] Redis read error: %s", e)
        return {"running": False, "current": 0, "total": 0, "percentage": 0, "story_id": None, "cancelled": False}
    finally:
        if r:
            await r.close()


async def set_reprocess_state(
    running: Optional[bool] = None,
    current: Optional[int] = None,
    total: Optional[int] = None,
    percentage: Optional[int] = None,
    story_id: Optional[int] = None,
    cancelled: Optional[bool] = None,
    state: Optional[dict] = None,
):
    """Set the current reprocess state in Redis.

    Accepts either keyword arguments or a state dict.
    If state dict is provided, it takes precedence.
    """
    if state is not None:
        payload = state
    else:
        current_state = await get_reprocess_state()
        payload = dict(current_state)
        if running is not None:
            payload["running"] = running
        if current is not None:
            payload["current"] = current
        if total is not None:
            payload["total"] = total
        if percentage is not None:
            payload["percentage"] = percentage
        if story_id is not None:
            payload["story_id"] = story_id
        if cancelled is not None:
            payload["cancelled"] = cancelled

    r = None
    try:
        r = await _get_redis()
        await r.set(REDIS_REPROCESS_STATUS_KEY, json.dumps(payload))
    except Exception as e:
        logger.error("[ReprocessState] Redis write error: %s", e)
    finally:
        if r:
            await r.close()


async def reset_reprocess_state():
    """Reset the reprocess state to idle."""
    await set_reprocess_state(
        running=False,
        current=0,
        total=0,
        percentage=0,
        story_id=None,
        cancelled=False,
    )