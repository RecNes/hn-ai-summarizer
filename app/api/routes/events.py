"""Server-Sent Events endpoint for real-time story updates.

Worker publishes to Redis Pub/Sub (using redis-py's asyncio support).
Frontend subscribes via SSE for real-time updates.
Falls back to keepalive-only if Redis is unavailable.
"""

import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.core.config import settings

router = APIRouter()

STORY_CHANNEL = "hn_reader:story:new"

async def _get_redis():
    """Create a redis asyncio connection from settings."""
    from redis.asyncio import Redis
    redis_url = settings.REDIS_CONNECTION_URL or "redis://localhost:6379/0"
    return Redis.from_url(redis_url, decode_responses=True)


async def event_generator(request: Request):
    """SSE generator: subscribe to Redis Pub/Sub, forward events to client."""
    r = None
    pubsub = None

    try:
        r = await _get_redis()
        pubsub = r.pubsub()
        await pubsub.subscribe(STORY_CHANNEL)

        yield "event: connected\ndata: {}\n\n"

        async for message in pubsub.listen():
            if await request.is_disconnected():
                break
            if message["type"] == "message":
                data = message.get("data", "")
                if isinstance(data, bytes):
                    data = data.decode()
                yield f"event: new_story\ndata: {data}\n\n"
    except Exception as e:
        print(f"[SSE] Redis unavailable, using keepalive only: {e}")
        while not await request.is_disconnected():
            yield ": keepalive\n\n"
            await asyncio.sleep(30)
    finally:
        if pubsub:
            try:
                await pubsub.unsubscribe(STORY_CHANNEL)
                await pubsub.close()
            except Exception:
                pass
        if r:
            await r.close()


@router.get("/stream")
async def stream_events(request: Request):
    """SSE endpoint: GET /api/events/stream"""
    return StreamingResponse(
        event_generator(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
