"""Scheduler tasks for periodic jobs

Uses aioscheduler.TimedScheduler for reliable async scheduling.
"""

import asyncio
import os
from datetime import datetime

from arq import create_pool
from arq.connections import RedisSettings
from sqlalchemy.future import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.setting import Setting
from app.tasks.schedule_manager import get_schedule_manager

# Debug logs only in development mode
_DEV = os.getenv("DEVELOPMENT", "false").lower() in ("true", "1", "yes", "on")


def _debug(*args, **kwargs):
    if _DEV:
        print(*args, **kwargs)


async def get_settings():
    """Get application settings from database"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Setting).limit(1))
        setting = result.scalar_one_or_none()
        await db.commit()
        return setting


async def initialize_schedule_from_db():
    """Initialize schedule from database settings and store in Redis"""
    setting = await get_settings()
    cron_schedule = (
        setting.cron_schedule if setting and setting.cron_schedule else "0 9 * * *"
    )

    schedule_manager = await get_schedule_manager()
    await schedule_manager.update_schedule(cron_schedule)

    print(f"Initialized schedule from database: {cron_schedule}")


def parse_cron_to_time(cron_schedule: str) -> str:
    """Parse cron schedule to time string for scheduling"""
    parts = cron_schedule.split()
    if len(parts) != 5:
        return "09:00"

    minute, hour, _, _, _ = parts

    try:
        hour_int = int(hour) if hour.isdigit() else 9
        minute_int = int(minute) if minute.isdigit() else 0
        return f"{hour_int:02d}:{minute_int:02d}"
    except ValueError:
        return "09:00"


def parse_cron_to_days(cron_schedule: str) -> list:
    """Parse cron schedule to get list of weekdays (cron: 0=Sunday)"""
    parts = cron_schedule.split()
    if len(parts) != 5:
        return [1, 2, 3, 4, 5]

    _, _, _, _, weekday_part = parts

    if weekday_part == "*":
        return []
    elif "," in weekday_part:
        try:
            return [int(day) for day in weekday_part.split(",") if day.isdigit()]
        except ValueError:
            return []
    elif "-" in weekday_part:
        try:
            start, end = map(int, weekday_part.split("-"))
            return list(range(start, end + 1))
        except ValueError:
            return []
    elif weekday_part.isdigit():
        return [int(weekday_part)]
    else:
        return []


def format_days_to_cron(days: list, hour: int, minute: int) -> str:
    """Format days, hour, minute to cron schedule"""
    if not days:
        return ""
    weekday_part = ",".join(map(str, sorted(days)))
    return f"{minute} {hour} * * {weekday_part}"


async def run_scheduler():
    """Run the scheduler with Redis-based schedule management."""
    print("Initializing schedule from database...")
    await initialize_schedule_from_db()

    # Catch-up: check if today's scheduled time has already passed
    try:
        schedule_manager = await get_schedule_manager()
        config = await schedule_manager.get_schedule_config()
        if config and config.get("cron_schedule"):
            cron_schedule = config["cron_schedule"]
            scheduled_time = parse_cron_to_time(cron_schedule)
            scheduled_days = parse_cron_to_days(cron_schedule)

            now = datetime.now()
            today_cron_weekday = (now.weekday() + 1) % 7
            current_time_minutes = now.hour * 60 + now.minute

            try:
                parts = scheduled_time.split(":")
                scheduled_minutes = int(parts[0]) * 60 + int(parts[1])
            except (ValueError, IndexError):
                scheduled_minutes = None

            days_match = not scheduled_days or today_cron_weekday in scheduled_days
            if (
                days_match
                and scheduled_minutes is not None
                and current_time_minutes >= scheduled_minutes
            ):
                print(
                    f"Catch-up: scheduled time {scheduled_time} has passed, triggering immediate fetch..."
                )
                redis_url = settings.REDIS_CONNECTION_URL or "redis://localhost:6379/0"
                redis_settings = RedisSettings.from_dsn(redis_url)
                catchup_pool = await create_pool(redis_settings)
                try:
                    job = await catchup_pool.enqueue_job("fetch_and_process_stories")
                    if job:
                        print(">>> Catch-up fetch job enqueued successfully")
                    else:
                        print(">>> Catch-up fetch job enqueue returned None")
                except Exception as e:
                    print(f">>> Error enqueuing catch-up fetch job: {e}")
                finally:
                    await catchup_pool.close()
    except Exception as e:
        print(f"Error during catch-up check: {e}")

    # Monitor schedule changes in background
    print("Starting schedule change monitoring...")
    monitor_task = asyncio.create_task(_monitor_schedule_changes())

    try:
        # Keep the scheduler alive by sleeping forever
        # aioscheduler.TimedScheduler runs its own loop internally
        while True:
            await asyncio.sleep(60)
            _debug("Scheduler alive check...")
    finally:
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass


async def _monitor_schedule_changes():
    """Monitor schedule changes in the background."""
    schedule_manager = await get_schedule_manager()
    await schedule_manager.monitor_schedule_changes()