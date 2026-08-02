"""Schedule helper — thin wrapper for settings API to update Redis schedule.

The actual scheduler logic lives in app.tasks.scheduler.
This module exists only to provide update_schedule() for the settings API.
"""

import json
import logging

from arq import create_pool
from arq.connections import RedisSettings

from app.core.config import settings as app_settings

logger = logging.getLogger(__name__)

SCHEDULE_KEY = "nunti:schedule:config"
VERSION_KEY = "nunti:schedule:version"


async def _get_redis_pool():
    """Create a short-lived Redis connection pool."""
    url = app_settings.REDIS_CONNECTION_URL or "redis://localhost:6379/0"
    return await create_pool(RedisSettings.from_dsn(url))


async def update_schedule(cron_schedule: str) -> bool:
    """Write schedule config to Redis and bump the version so the scheduler picks it up."""
    try:
        pool = await _get_redis_pool()
    except Exception as e:
        logger.error("[ScheduleHelper] Failed to connect to Redis: %s", e)
        return False

    try:
        await pool.set(  # type: ignore[union-attr]
            SCHEDULE_KEY, json.dumps({"cron_schedule": cron_schedule})
        )
        v = await pool.get(VERSION_KEY)  # type: ignore[union-attr]
        new_v = str(int(v) + 1 if v else 1)
        await pool.set(VERSION_KEY, new_v)  # type: ignore[union-attr]
        logger.info("[ScheduleHelper] Updated Redis schedule: %s (version=%s)", cron_schedule, new_v)
        return True
    except Exception as e:
        logger.error("[ScheduleHelper] Error updating schedule: %s", e)
        return False
    finally:
        await pool.aclose()