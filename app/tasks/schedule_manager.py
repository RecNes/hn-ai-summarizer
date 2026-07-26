"""Redis-based schedule manager for sharing schedule state between processes.

Uses own asyncio-based scheduler (aioscheduler is incompatible with Python 3.14+).
"""

import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta

from arq import create_pool
from arq.connections import RedisSettings

from app.core.config import settings

logger = logging.getLogger(__name__)

# Redis keys for schedule management
SCHEDULE_KEY = "hn_reader:schedule:config"
SCHEDULE_LOCK_KEY = "hn_reader:schedule:lock"
SCHEDULE_VERSION_KEY = "hn_reader:schedule:version"

# Lock timeout in seconds
LOCK_TIMEOUT = 10

# Cron weekday → day name mapping
WEEKDAY_NAMES = [
    "sunday", "monday", "tuesday", "wednesday",
    "thursday", "friday", "saturday",
]

# ── Own Simple Scheduler (replaces aioscheduler) ──────────
# aioscheduler uses asyncio.wait(coroutines) which is forbidden in Python 3.14+.
# We use asyncio.sleep() in a background task instead.


class _ScheduledTask:
    """A single scheduled task reference."""
    def __init__(self, coro, target_dt):
        self.coro = coro
        self.target_dt = target_dt
        self._bg_task = None

    def cancel(self):
        if self._bg_task and not self._bg_task.done():
            self._bg_task.cancel()
            self._bg_task = None


_scheduled_tasks: list[_ScheduledTask] = []


async def _run_scheduled_coro(coro):
    """Run the coroutine safely."""
    try:
        await coro
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(">>> [SchedulerTask] Error in scheduled job: %s", e)
        import traceback
        traceback.print_exc()


def _schedule_coro(coro, when: datetime):
    """Schedule a coroutine to run at `when` (naive local datetime).
    
    Returns a _ScheduledTask that can be cancelled.
    """
    now = datetime.now()
    delay = max(0, (when - now).total_seconds())

    task = _ScheduledTask(coro, when)

    async def _delayed_run():
        if delay > 0:
            await asyncio.sleep(delay)
        await _run_scheduled_coro(coro)

    bg_task = asyncio.create_task(_delayed_run())
    task._bg_task = bg_task
    _scheduled_tasks.append(task)
    logger.debug(">>> [OwnScheduler] Scheduled coro in %.1fs (target=%s)", delay, when.isoformat())
    return task


def _cancel_all_scheduled():
    """Cancel all scheduled tasks."""
    for t in _scheduled_tasks:
        t.cancel()
    _scheduled_tasks.clear()
    logger.info(">>> [OwnScheduler] Cancelled all scheduled tasks")


# ── Helper: schedule job from a sync factory function ──
# This avoids the Python 3.14 "coroutine never awaited" warning:
# the factory is NOT async, it returns a coroutine that gets awaited inside _schedule_coro.


def _schedule_job_from_factory(factory_func, target_dt: datetime):
    """Schedule a job via a factory function that returns a coroutine.
    
    factory_func: a sync callable that returns a coroutine.
    Usage: _schedule_job_from_factory(lambda: my_coro(), target)
    """
    def _factory_wrapper():
        return _run_scheduled_coro(factory_func())
    return _schedule_coro(_factory_wrapper(), target_dt)


class ScheduleManager:
    """Manages schedule configuration in Redis and synchronizes between processes."""

    def __init__(self):
        self.redis_pool = None
        self._schedule_version = None
        self._is_initialized = False

    async def initialize(self):
        """Initialize Redis connection."""
        if not self._is_initialized:
            redis_url = settings.REDIS_CONNECTION_URL or "redis://localhost:6379/0"
            redis_settings = RedisSettings.from_dsn(redis_url)
            self.redis_pool = await create_pool(redis_settings)
            self._is_initialized = True
            logger.info(">>> [ScheduleManager] Initialized with Redis")

    async def get_schedule_config(self) -> dict | None:
        """Get current schedule configuration from Redis."""
        await self.initialize()

        try:
            config_data = await self.redis_pool.get(SCHEDULE_KEY)  # type: ignore
            if config_data:
                config = json.loads(config_data)
                logger.debug(">>> [ScheduleManager] Retrieved config: %s", config)
                return config
            logger.debug(">>> [ScheduleManager] No config in Redis")
            return None
        except Exception as e:
            logger.error(">>> [ScheduleManager] Error getting config: %s", e)
            return None

    async def set_schedule_config(self, config: dict):
        """Set schedule configuration in Redis."""
        await self.initialize()

        try:
            config_data = json.dumps(config)
            await self.redis_pool.set(SCHEDULE_KEY, config_data)  # type: ignore

            # Increment version for cache invalidation
            version = await self.redis_pool.get(SCHEDULE_VERSION_KEY)  # type: ignore
            new_version = str(int(version) + 1 if version else 1)
            await self.redis_pool.set(SCHEDULE_VERSION_KEY, new_version)  # type: ignore

            logger.info(">>> [ScheduleManager] Updated config: %s (version=%s)", config, new_version)
        except Exception as e:
            logger.error(">>> [ScheduleManager] Error setting config: %s", e)
            raise

    async def get_schedule_version(self) -> str:
        """Get current schedule version from Redis."""
        await self.initialize()

        try:
            version = await self.redis_pool.get(SCHEDULE_VERSION_KEY)  # type: ignore
            return version or "0"
        except Exception as e:
            logger.error(">>> [ScheduleManager] Error getting version: %s", e)
            return "0"

    async def acquire_lock(self) -> bool:
        """Acquire schedule modification lock."""
        await self.initialize()

        try:
            result = await self.redis_pool.set(  # type: ignore
                SCHEDULE_LOCK_KEY, "1", nx=True, ex=LOCK_TIMEOUT
            )
            return result is True
        except Exception as e:
            logger.error(">>> [ScheduleManager] Error acquiring lock: %s", e)
            return False

    async def release_lock(self):
        """Release schedule modification lock."""
        await self.initialize()

        try:
            await self.redis_pool.delete(SCHEDULE_LOCK_KEY)  # type: ignore
            logger.debug(">>> [ScheduleManager] Released lock")
        except Exception as e:
            logger.error(">>> [ScheduleManager] Error releasing lock: %s", e)

    async def clear_schedule(self):
        """Cancel all scheduled tasks."""
        _cancel_all_scheduled()
        logger.info(">>> [ScheduleManager] Cleared all scheduled tasks")

    async def apply_schedule_from_redis(self):
        """Apply schedule configuration from Redis to the local scheduler."""
        config = await self.get_schedule_config()
        if not config:
            logger.warning(">>> [ScheduleManager] No schedule config found in Redis")
            return False

        try:
            await self.clear_schedule()

            cron_schedule = config.get("cron_schedule")
            if not cron_schedule:
                logger.info(">>> [ScheduleManager] No cron schedule configured, skipping")
                return True

            from app.tasks.scheduler import parse_cron_to_days, parse_cron_to_time

            scheduled_time = parse_cron_to_time(cron_schedule)
            scheduled_days = parse_cron_to_days(cron_schedule)

            logger.info(">>> [ScheduleManager] Parsed cron: time=%s days=%s (raw=%s)",
                        scheduled_time, scheduled_days, cron_schedule)

            if not scheduled_days:
                logger.info(">>> [ScheduleManager] No days selected, skipping scheduling")
                return True

            for day_num in scheduled_days:
                day_name = WEEKDAY_NAMES[day_num]

                # Factory: sync function returns a coroutine (avoids Python 3.14 "never awaited" warning)
                def _make_job_coro(day=day_name, time_str=scheduled_time):
                    async def _job():
                        logger.info(">>> [ScheduleManager] ⏰ JOB TRIGGERED for %s at %s", day, time_str)
                        await _enqueue_fetch_job(day)
                        await _reschedule_job(day, time_str)
                        logger.info(">>> [ScheduleManager] ✅ Job completed for %s", day)
                    return _job()

                # Calculate next occurrence in naive local time
                now_naive = datetime.now().replace(microsecond=0)
                target = _next_weekday_time_local_naive(now_naive, day_num, scheduled_time)

                logger.info(">>> [ScheduleManager] Scheduling %s: target=%s, time_str=%s",
                            day_name, target.isoformat(), scheduled_time)
                _schedule_coro(_make_job_coro(), target)
                logger.info(">>> [ScheduleManager] ✅ Task scheduled for %s at %s (next: %s)",
                            day_name, scheduled_time, target)

            self._schedule_version = await self.get_schedule_version()
            logger.info(">>> [ScheduleManager] Applied schedule: %s", cron_schedule)
            return True

        except Exception as e:
            logger.error(">>> [ScheduleManager] Error applying schedule: %s", e)
            import traceback
            traceback.print_exc()
            return False

    async def update_schedule(self, cron_schedule: str):
        """Update schedule configuration and apply it locally."""
        if not await self.acquire_lock():
            logger.warning(">>> [ScheduleManager] Could not acquire lock, another process may be updating")
            return False

        try:
            config = {
                "cron_schedule": cron_schedule,
                "updated_at": asyncio.get_event_loop().time(),
            }

            await self.set_schedule_config(config)
            success = await self.apply_schedule_from_redis()

            if success:
                logger.info(">>> [ScheduleManager] Successfully updated schedule: %s", cron_schedule)
            else:
                logger.error(">>> [ScheduleManager] Failed to apply schedule locally")

            return success

        finally:
            await self.release_lock()

    async def monitor_schedule_changes(self):
        """Monitor Redis for schedule changes and update local scheduler."""
        await self.initialize()

        logger.info(">>> [ScheduleManager] Starting change monitor (polling every 5s)")

        while True:
            try:
                current_version = await self.get_schedule_version()

                if self._schedule_version is None:
                    logger.info(">>> [ScheduleManager] First run → applying schedule")
                    await self.apply_schedule_from_redis()
                    self._schedule_version = current_version
                elif current_version != self._schedule_version:
                    logger.info(">>> [ScheduleManager] Version changed: %s → %s, reloading",
                                self._schedule_version, current_version)
                    await self.apply_schedule_from_redis()
                    self._schedule_version = current_version

                await asyncio.sleep(5)
            except Exception as e:
                logger.error(">>> [ScheduleManager] Monitor error: %s", e)
                await asyncio.sleep(10)


# ── Helpers ──────────────────────────────


def _next_weekday_time_local_naive(now_naive: datetime, target_weekday: int, time_str: str) -> datetime:
    """Calculate the next occurrence of target_weekday at time_str (naive local).

    Cron weekday mapping: 0=Sunday..6=Saturday.
    FIX: If today is the target day and the time hasn't passed yet, schedule for TODAY.
    """
    parts = time_str.split(":")
    hour = int(parts[0])
    minute = int(parts[1]) if len(parts) > 1 else 0

    # Python weekday: 0=Monday..6=Sunday
    # cron weekday: 0=Sunday..6=Saturday → convert: (cron + 6) % 7 = Python
    current_py_weekday = now_naive.weekday()
    target_py = (target_weekday + 6) % 7

    days_ahead = target_py - current_py_weekday
    if days_ahead < 0:
        days_ahead += 7
    # days_ahead == 0: today is the target day

    target = now_naive.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=days_ahead)
    
    # If the calculated time has already passed today, push to next week
    if target < now_naive:
        target += timedelta(days=7)
        
    logger.debug(">>> [Helper] _next_weekday_time: now=%s wday=%s time=%s → target=%s",
                 now_naive.isoformat(), target_weekday, time_str, target.isoformat())
    return target


async def _enqueue_fetch_job(day_name: str):
    """Enqueue a fetch_and_process_stories job via Arq."""
    logger.info(">>> [ScheduleManager] 🔄 _enqueue_fetch_job for %s", day_name)
    try:
        redis_url = settings.REDIS_CONNECTION_URL or "redis://localhost:6379/0"
        redis_settings = RedisSettings.from_dsn(redis_url)
        pool = await create_pool(redis_settings)

        job = await pool.enqueue_job("fetch_and_process_stories")
        if job:
            logger.info(">>> [ScheduleManager] ✅ Worker job enqueued for %s (job=%s)", day_name, job)
        else:
            logger.info(">>> [ScheduleManager] ❌ Worker job enqueue returned None for %s", day_name)

        await pool.aclose()
    except Exception as e:
        logger.error(">>> [ScheduleManager] ❌ Error enqueuing job for %s: %s", day_name, e)
        import traceback
        traceback.print_exc()


async def _reschedule_job(day_name: str, scheduled_time: str):
    """Reschedule the job for the next week on the same day at the correct time."""
    day_num = WEEKDAY_NAMES.index(day_name)
    logger.info(">>> [ScheduleManager] 🔄 _reschedule_job: day=%s num=%s time=%s",
                day_name, day_num, scheduled_time)

    now_naive = datetime.now().replace(microsecond=0)
    target = _next_weekday_time_local_naive(now_naive, day_num, scheduled_time)
    
    # If target ≤ now, push to next week to avoid infinite re-trigger
    if target <= now_naive:
        target += timedelta(days=7)

    logger.info(">>> [ScheduleManager] Rescheduling %s: next target=%s", day_name, target.isoformat())

    # Use _schedule_job_from_factory to avoid Python 3.14 "never awaited" warning
    def _make_weekly_coro(day=day_name, time_str=scheduled_time):
        async def _weekly_job():
            logger.info(">>> [ScheduleManager] ⏰ Weekly job triggered for %s at %s", day, time_str)
            await _enqueue_fetch_job(day)
            await _reschedule_job(day, time_str)
        return _weekly_job()

    _schedule_coro(_make_weekly_coro(), target)
    logger.info(">>> [ScheduleManager] ✅ Rescheduled %s for %s (next: %s)", day_name, scheduled_time, target)


# ── Factory ──────────────────────────────


async def get_schedule_manager() -> ScheduleManager:
    """Get the global schedule manager instance."""
    manager = ScheduleManager()
    await manager.initialize()
    return manager