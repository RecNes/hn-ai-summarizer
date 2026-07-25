"""Redis-based reprocess state management."""

import json
import logging
import time
from typing import Optional

from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)

REDIS_REPROCESS_STATUS_KEY = "hn_reader:reprocess:status"

# Bir stream bağlantısı bu süre (saniye) boyunca heartbeat göndermezse
# stuck kabul edilir ve 409 yerine yeni stream'e izin verilir.
REPROCESS_HEARTBEAT_TIMEOUT = 60


async def _get_redis() -> Redis:
    """Create a redis asyncio connection."""
    redis_url = settings.REDIS_CONNECTION_URL or "redis://localhost:6379/0"
    return Redis.from_url(redis_url, decode_responses=True)


async def get_reprocess_state() -> dict:
    """Get the current reprocess state from Redis.

    Stuck state auto-recovery: Eğer running=True ama son heartbeat
    REPROCESS_HEARTBEAT_TIMEOUT saniyeden daha eskiyse state otomatik
    resetlenir ve yeni stream bağlantısına izin verilir.
    """
    r = None
    try:
        r = await _get_redis()
        data = await r.get(REDIS_REPROCESS_STATUS_KEY)
        if data:
            state = json.loads(data)
            # ── Stuck state auto-recovery ──────────────────────
            if state.get("running"):
                last_hb = state.get("last_heartbeat")
                if last_hb and (time.time() - last_hb) > REPROCESS_HEARTBEAT_TIMEOUT:
                    logger.warning(
                        "[ReprocessState] Stuck state detected (last heartbeat %.0fs ago). Auto-resetting.",
                        time.time() - last_hb,
                    )
                    state = {
                        "running": False,
                        "current": 0,
                        "total": 0,
                        "percentage": 0,
                        "story_id": None,
                        "cancelled": False,
                        "last_heartbeat": None,
                    }
                    await r.set(REDIS_REPROCESS_STATUS_KEY, json.dumps(state))
                elif not last_hb:
                    # last_heartbeat yoksa da stuck kabul et ve resetle
                    logger.warning("[ReprocessState] State has running=True but no heartbeat. Auto-resetting.")
                    state = {
                        "running": False,
                        "current": 0,
                        "total": 0,
                        "percentage": 0,
                        "story_id": None,
                        "cancelled": False,
                        "last_heartbeat": None,
                    }
                    await r.set(REDIS_REPROCESS_STATUS_KEY, json.dumps(state))
            # ──────────────────────────────────────────────────
            return state
        return {
            "running": False,
            "current": 0,
            "total": 0,
            "percentage": 0,
            "story_id": None,
            "cancelled": False,
            "last_heartbeat": None,
        }
    except Exception as e:
        logger.error("[ReprocessState] Redis read error: %s", e)
        return {
            "running": False,
            "current": 0,
            "total": 0,
            "percentage": 0,
            "story_id": None,
            "cancelled": False,
            "last_heartbeat": None,
        }
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

    # running=True olan her yazma işleminde heartbeat zaman damgasını güncelle
    if payload.get("running"):
        payload["last_heartbeat"] = time.time()

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