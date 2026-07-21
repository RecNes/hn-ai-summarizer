"""Redis-based schedule manager for sharing schedule state between processes.

Uses aioscheduler (TimedScheduler) instead of the deprecated aioschedule
to avoid Python 3.11+ "async.wait coroutine forbidden" errors.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from aioscheduler import TimedScheduler
from arq.connections import RedisSettings
from arq import create_pool

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

# Global scheduler state — encapsulated via accessor functions
_scheduler: Optional[TimedScheduler] = None
_scheduler_tasks: List = []


def _get_scheduler() -> Optional[TimedScheduler]:
    """Return the global TimedScheduler instance."""
    return _scheduler


def _set_scheduler(instance: Optional[TimedScheduler]) -> None:
    """Set the global TimedScheduler instance."""
    global _scheduler  # pylint: disable=global-statement
    _scheduler = instance


def _get_scheduler_tasks() -> List:
    """Return the list of scheduled task objects."""
    return _scheduler_tasks


def _set_scheduler_tasks(tasks: List) -> None:
    """Replace the global scheduled tasks list."""
    global _scheduler_tasks  # pylint: disable=global-statement
    _scheduler_tasks = tasks


def _clear_scheduler_tasks() -> None:
    """Empty the scheduled tasks list."""
    global _scheduler_tasks  # pylint: disable=global-statement
    _scheduler_tasks = []


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
            logger.info("ScheduleManager initialized with Redis")

    async def get_schedule_config(self) -> Optional[Dict]:
        """Get current schedule configuration from Redis."""
        await self.initialize()

        try:
            config_data = await self.redis_pool.get(SCHEDULE_KEY)  # type: ignore
            if config_data:
                config = json.loads(config_data)
                logger.debug(f"Retrieved schedule config: {config}")
                return config
            return None
        except Exception as e:
            logger.error(f"Error getting schedule config: {e}")
            return None

    async def set_schedule_config(self, config: Dict):
        """Set schedule configuration in Redis."""
        await self.initialize()

        try:
            config_data = json.dumps(config)
            await self.redis_pool.set(SCHEDULE_KEY, config_data)  # type: ignore

            # Increment version for cache invalidation
            version = await self.redis_pool.get(SCHEDULE_VERSION_KEY)  # type: ignore
            new_version = str(int(version) + 1 if version else 1)
            await self.redis_pool.set(SCHEDULE_VERSION_KEY, new_version)  # type: ignore

            logger.info(f"Updated schedule config: {config}")
        except Exception as e:
            logger.error(f"Error setting schedule config: {e}")
            raise

    async def get_schedule_version(self) -> str:
        """Get current schedule version from Redis."""
        await self.initialize()

        try:
            version = await self.redis_pool.get(SCHEDULE_VERSION_KEY)  # type: ignore
            return version or "0"
        except Exception as e:
            logger.error(f"Error getting schedule version: {e}")
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
            logger.error(f"Error acquiring schedule lock: {e}")
            return False

    async def release_lock(self):
        """Release schedule modification lock."""
        await self.initialize()

        try:
            await self.redis_pool.delete(SCHEDULE_LOCK_KEY)  # type: ignore
            logger.debug("Released schedule lock")
        except Exception as e:
            logger.error(f"Error releasing schedule lock: {e}")

    async def clear_schedule(self):
        """Cancel all scheduled tasks in the global scheduler."""
        scheduler = _get_scheduler()
        task_refs = _get_scheduler_tasks()
        for task_ref in task_refs:
            try:
                if scheduler:
                    scheduler.cancel(task_ref)
                if hasattr(task_ref, 'callback') and hasattr(task_ref.callback, 'close'):
                    task_ref.callback.close()
            except Exception as e:
                logger.debug(f"Error cancelling task: {e}")
        _clear_scheduler_tasks()
        logger.info("Cleared all scheduled tasks")

    async def apply_schedule_from_redis(self):
        """Apply schedule configuration from Redis to the global scheduler."""
        config = await self.get_schedule_config()
        if not config:
            logger.warning("No schedule configuration found in Redis")
            return False

        try:
            await self.clear_schedule()

            cron_schedule = config.get("cron_schedule")
            if not cron_schedule:
                logger.info("No cron schedule configured, skipping scheduling")
                return True

            from app.tasks.scheduler import parse_cron_to_time, parse_cron_to_days

            scheduled_time = parse_cron_to_time(cron_schedule)
            scheduled_days = parse_cron_to_days(cron_schedule)

            if not scheduled_days:
                logger.info("No days selected for scheduling")
                return True

            scheduler = _get_scheduler()
            if scheduler is None:
                scheduler = TimedScheduler(prefer_utc=False)
                scheduler.start()
                _set_scheduler(scheduler)

            task_refs = _get_scheduler_tasks()

            for day_num in scheduled_days:
                day_name = WEEKDAY_NAMES[day_num]

                async def job_wrapper(day=day_name):
                    await _enqueue_fetch_job(day)
                    _reschedule_job(day)

                now = datetime.now()
                target = _next_weekday_time(now, day_num, scheduled_time)
                if target < now:
                    target += timedelta(days=7)

                task_obj = scheduler.schedule(job_wrapper(), target)
                task_refs.append(task_obj)
                logger.info(f"Scheduled task for {day_name} at {scheduled_time} (next: {target})")

            self._schedule_version = await self.get_schedule_version()
            logger.info(f"Applied schedule from Redis: {cron_schedule}")
            return True

        except Exception as e:
            logger.error(f"Error applying schedule from Redis: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def update_schedule(self, cron_schedule: str):
        """Update schedule configuration and apply it locally."""
        if not await self.acquire_lock():
            logger.warning(
                "Could not acquire schedule lock, another process may be updating"
            )
            return False

        try:
            config = {
                "cron_schedule": cron_schedule,
                "updated_at": asyncio.get_event_loop().time(),
            }

            await self.set_schedule_config(config)
            success = await self.apply_schedule_from_redis()

            if success:
                logger.info(f"Successfully updated and applied schedule: {cron_schedule}")
            else:
                logger.error("Failed to apply schedule locally")

            return success

        finally:
            await self.release_lock()

    async def monitor_schedule_changes(self):
        """Monitor Redis for schedule changes and update local scheduler."""
        await self.initialize()

        logger.info("Starting schedule change monitoring")

        while True:
            try:
                current_version = await self.get_schedule_version()

                if self._schedule_version is None:
                    await self.apply_schedule_from_redis()
                    self._schedule_version = current_version
                elif current_version != self._schedule_version:
                    logger.info("Schedule change detected, reloading...")
                    await self.apply_schedule_from_redis()
                    self._schedule_version = current_version

                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Error monitoring schedule changes: {e}")
                await asyncio.sleep(10)


# ── Helpers ──────────────────────────────


def _next_weekday_time(now: datetime, target_weekday: int, time_str: str) -> datetime:
    """Calculate the next occurrence of target_weekday at time_str.

    aioscheduler weekday: 0=Sunday..6=Saturday (matches cron).
    """
    parts = time_str.split(":")
    hour = int(parts[0])
    minute = int(parts[1]) if len(parts) > 1 else 0

    # Python weekday: 0=Monday..6=Sunday
    # cron weekday: 0=Sunday..6=Saturday
    current_py_weekday = now.weekday()
    target_py = (target_weekday + 6) % 7  # cron→python: -1 mod 7

    days_ahead = target_py - current_py_weekday
    if days_ahead <= 0:
        days_ahead += 7

    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=days_ahead)
    return target


async def _enqueue_fetch_job(day_name: str):
    """Enqueue a fetch_and_process_stories job via Arq."""
    logger.info(f"Job triggered for {day_name}")
    try:
        redis_url = settings.REDIS_CONNECTION_URL or "redis://localhost:6379/0"
        redis_settings = RedisSettings.from_dsn(redis_url)
        pool = await create_pool(redis_settings)

        job = await pool.enqueue_job("fetch_and_process_stories")
        if job:
            logger.info(f">>> Worker job enqueued successfully for {day_name}")
        else:
            logger.info(f">>> Failed to enqueue worker job for {day_name}")

        await pool.close()
    except Exception as e:
        logger.error(f">>> Error enqueuing worker job for {day_name}: {e}")


def _reschedule_job(day_name: str):
    """Reschedule the job for the next week on the same day."""
    scheduler = _get_scheduler()
    if scheduler is None:
        return

    day_num = WEEKDAY_NAMES.index(day_name)

    now = datetime.now()
    target = _next_weekday_time(now, day_num, "09:00")

    async def job_wrapper(day=day_name):
        await _enqueue_fetch_job(day)
        _reschedule_job(day)

    task_obj = scheduler.schedule(job_wrapper(), target)
    task_refs = _get_scheduler_tasks()
    task_refs.append(task_obj)
    logger.info(f"Rescheduled {day_name} for {target}")


# ── Scheduler lifecycle ──────────────────


def get_global_scheduler() -> TimedScheduler:
    """Get or create the global TimedScheduler instance."""
    scheduler = _get_scheduler()
    if scheduler is None:
        scheduler = TimedScheduler(prefer_utc=False)
        scheduler.start()
        _set_scheduler(scheduler)
        logger.info("Created and started global TimedScheduler")
    return scheduler


async def get_schedule_manager() -> ScheduleManager:
    """Get the global schedule manager instance."""
    manager = ScheduleManager()
    await manager.initialize()
    return manager