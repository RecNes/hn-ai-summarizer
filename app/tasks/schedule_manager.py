"""Redis-based schedule manager for sharing schedule state between processes."""

import asyncio
import json
import logging
from typing import Dict, Optional

import aioschedule
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


class ScheduleManager:
    """Manages schedule configuration in Redis and synchronizes between processes."""

    def __init__(self):
        self.redis_pool = None
        self._schedule_version = None
        self._is_initialized = False

    async def initialize(self):
        """Initialize Redis connection."""
        if not self._is_initialized:
            redis_url = settings.REDIS_URL or "redis://localhost:6379/0"
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
            # Use SET with NX (set if not exists) and EX (expire) for atomic lock
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
        """Clear all scheduled jobs."""
        try:
            aioschedule.clear()
            logger.info("Cleared local aioschedule jobs")
        except Exception as e:
            logger.error(f"Error clearing local schedule: {e}")

    async def apply_schedule_from_redis(self):
        """Apply schedule configuration from Redis to local aioschedule."""
        await self.initialize()

        config = await self.get_schedule_config()
        if not config:
            logger.warning("No schedule configuration found in Redis")
            return False

        try:
            # Clear existing schedules
            await self.clear_schedule()

            # Apply new schedule
            cron_schedule = config.get("cron_schedule")
            if not cron_schedule:
                logger.info("No cron schedule configured, skipping scheduling")
                return True

            # Parse and schedule jobs (reuse existing logic)
            from app.tasks.scheduler import parse_cron_to_time, parse_cron_to_days

            scheduled_time = parse_cron_to_time(cron_schedule)
            scheduled_days = parse_cron_to_days(cron_schedule)

            if not scheduled_days:
                logger.info("No days selected for scheduling")
                return True

            # Connect to Redis for job execution
            redis_url = settings.REDIS_URL or "redis://localhost:6379/0"
            redis_settings = RedisSettings.from_dsn(redis_url)
            redis_pool = await create_pool(redis_settings)

            # Schedule jobs for each day
            for day_num in scheduled_days:
                day_name = [
                    "monday",
                    "tuesday",
                    "wednesday",
                    "thursday",
                    "friday",
                    "saturday",
                    "sunday",
                ][day_num]

                task_name = f"task for {day_name} at {scheduled_time}"
                logger.info(f"Scheduling {task_name}")

                async def create_job_closure(day_name=day_name, redis_pool=redis_pool):
                    """Create job closure to capture day_name and redis_pool."""
                    from app.tasks.scheduler import create_job_for_day

                    await create_job_for_day(day_name, redis_pool)

                getattr(aioschedule.every(), day_name).at(scheduled_time).do(
                    lambda: asyncio.create_task(create_job_closure())
                )

            # Update local version tracking
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
        # Try to acquire lock
        if not await self.acquire_lock():
            logger.warning(
                "Could not acquire schedule lock, another process may be updating"
            )
            return False

        try:
            # Prepare new configuration
            config = {
                "cron_schedule": cron_schedule,
                "updated_at": asyncio.get_event_loop().time(),
            }

            # Update Redis
            await self.set_schedule_config(config)

            # Apply to local scheduler
            success = await self.apply_schedule_from_redis()

            if success:
                logger.info(
                    f"Successfully updated and applied schedule: {cron_schedule}"
                )
            else:
                logger.error("Failed to apply schedule locally")

            return success

        finally:
            # Always release lock
            await self.release_lock()

    async def monitor_schedule_changes(self):
        """Monitor Redis for schedule changes and update local scheduler."""
        await self.initialize()

        logger.info("Starting schedule change monitoring")

        while True:
            try:
                # Check if version has changed
                current_version = await self.get_schedule_version()

                if self._schedule_version is None:
                    # First run - apply current schedule
                    await self.apply_schedule_from_redis()
                    self._schedule_version = current_version
                elif current_version != self._schedule_version:
                    # Schedule has changed - reload
                    logger.info("Schedule change detected, reloading...")
                    await self.apply_schedule_from_redis()
                    self._schedule_version = current_version

                # Wait before next check
                await asyncio.sleep(5)  # Check every 5 seconds

            except Exception as e:
                logger.error(f"Error monitoring schedule changes: {e}")
                await asyncio.sleep(10)  # Wait longer on error


# Global schedule manager instance
schedule_manager = ScheduleManager()


async def get_schedule_manager() -> ScheduleManager:
    """Get the global schedule manager instance."""
    await schedule_manager.initialize()
    return schedule_manager
