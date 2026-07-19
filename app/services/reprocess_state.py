"""Redis-backed reprocess job state.

Survives server restarts and page refreshes.
Uses hash key 'reprocess:state' with fields:
  - running (str '1'/'0')
  - current (str)
  - total (str)
  - percentage (str)
  - story_id (str)
  - cancelled (str '1'/'0')
"""

from app.core.config import settings


def _redis_key() -> str:
    return "reprocess:state"


def _unhash(data: dict) -> dict:
    """Convert Redis hash back to typed dict."""
    return {
        "running": data.get("running", "0") == "1",
        "current": int(data.get("current", 0)),
        "total": int(data.get("total", 0)),
        "percentage": int(data.get("percentage", 0)),
        "story_id": int(data.get("story_id", 0)) if data.get("story_id", "0") != "None" else None,
        "cancelled": data.get("cancelled", "0") == "1",
    }


async def get_reprocess_state() -> dict:
    """Read current reprocess state from Redis."""
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(
            settings.REDIS_CONNECTION_URL,
            decode_responses=True,
        )
        data = await r.hgetall(_redis_key())
        await r.aclose()
        if data:
            return _unhash(data)
        return {"running": False, "current": 0, "total": 0, "percentage": 0, "story_id": None, "cancelled": False}
    except Exception as e:
        print(f"[ReprocessState] Redis read error: {e}")
        return {"running": False, "current": 0, "total": 0, "percentage": 0, "story_id": None, "cancelled": False}


async def set_reprocess_state(**kwargs) -> None:
    """Write reprocess state to Redis.

    Always sets 'running' based on kwargs or keeps current value.
    Only the provided fields are updated; others remain unchanged.
    """
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(
            settings.REDIS_CONNECTION_URL,
            decode_responses=True,
        )

        # Read current state to merge
        current = await r.hgetall(_redis_key())
        if not current:
            current = {"running": "0", "current": "0", "total": "0", "percentage": "0", "story_id": "None", "cancelled": "0"}

        # Update with provided kwargs
        if "running" in kwargs:
            new_running = kwargs["running"]
            current["running"] = "1" if new_running else "0"

        for field in ("current", "total", "percentage", "story_id", "cancelled"):
            if field in kwargs:
                val = kwargs[field]
                current[field] = str(val) if val is not None else "None"

        await r.hset(_redis_key(), mapping=current)
        await r.aclose()
    except Exception as e:
        print(f"[ReprocessState] Redis write error: {e}")


async def reset_reprocess_state() -> None:
    """Reset all reprocess state fields to defaults."""
    await set_reprocess_state(
        running=False,
        current=0,
        total=0,
        percentage=0,
        story_id=None,
        cancelled=False,
    )