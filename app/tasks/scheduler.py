"""Scheduler tasks for periodic jobs"""

import asyncio
import os

import aioschedule
from sqlalchemy.future import select

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

    # Get schedule manager and update Redis
    schedule_manager = await get_schedule_manager()
    await schedule_manager.update_schedule(cron_schedule)

    print(f"Initialized schedule from database: {cron_schedule}")


def parse_cron_to_time(cron_schedule: str) -> str:
    """Parse cron schedule to time string for aioschedule"""
    # Cron format: "minute hour day month weekday"
    # We only care about minute and hour for daily scheduling
    parts = cron_schedule.split()
    if len(parts) != 5:
        return "09:00"  # Default time

    minute, hour, _, _, _ = parts

    # Convert to time format (HH:MM)
    try:
        hour_int = int(hour) if hour.isdigit() else 9
        minute_int = int(minute) if minute.isdigit() else 0
        return f"{hour_int:02d}:{minute_int:02d}"
    except ValueError:
        return "09:00"  # Default time if parsing fails


def parse_cron_to_days(cron_schedule: str) -> list:
    """Parse cron schedule to get list of weekdays (0=Monday, 6=Sunday)"""
    parts = cron_schedule.split()
    if len(parts) != 5:
        return [1, 2, 3, 4, 5]  # Default: weekdays (Mon-Fri)

    _, _, _, _, weekday_part = parts

    # Handle different cron weekday formats
    if weekday_part == "*":
        return []  # No specific days - meaning no scheduling
    elif "," in weekday_part:
        # Multiple days like "1,2,3"
        try:
            return [int(day) for day in weekday_part.split(",") if day.isdigit()]
        except ValueError:
            return []
    elif "-" in weekday_part:
        # Range like "1-5"
        try:
            start, end = map(int, weekday_part.split("-"))
            return list(range(start, end + 1))
        except ValueError:
            return []
    elif weekday_part.isdigit():
        # Single day
        return [int(weekday_part)]
    else:
        return []


def format_days_to_cron(days: list, hour: int, minute: int) -> str:
    """Format days, hour, minute to cron schedule"""
    if not days:
        return ""  # No scheduling when no days selected

    # Convert days list to cron weekday format
    weekday_part = ",".join(map(str, sorted(days)))

    return f"{minute} {hour} * * {weekday_part}"


# Create a closure to capture the current day_name and redis_pool
async def create_job_for_day(day_name, redis_pool):
    """Create and enqueue the worker job for the given day"""

    print(f"DEBUG: Job triggered for {day_name}")
    try:
        # Create fresh Redis connection for each job execution
        # redis_url = settings.REDIS_URL or "redis://localhost:6379/0"
        # redis_settings = RedisSettings.from_dsn(redis_url)
        # redis_pool = await create_pool(redis_settings)
        print("DEBUG: pool created in job", redis_pool, type(redis_pool))

        job = await redis_pool.enqueue_job("fetch_and_process_stories")
        print("DEBUG: Job enqueued", job, type(job))
        if job:
            print(f">>> Worker job enqueued successfully for {day_name}")
        else:
            print(f">>> Failed to enqueue worker job for {day_name}")

        await redis_pool.close()  # Clean up connection
    except Exception as e:
        print(f">>> Error enqueuing worker job for {day_name}: {e}")


async def schedule_worker(cron_schedule=None):
    """Schedule the worker based on settings using Redis-based schedule manager"""
    try:
        # Get schedule manager
        schedule_manager = await get_schedule_manager()

        if cron_schedule is not None:
            # Update schedule if provided
            success = await schedule_manager.update_schedule(cron_schedule)
            if not success:
                print("Failed to update schedule")
                return
        else:
            # Apply current schedule from Redis
            await schedule_manager.apply_schedule_from_redis()

        print(f"Scheduling worker with cron: {cron_schedule or 'from Redis'}")

    except Exception as e:
        print(f"Error scheduling worker: {e}")
        import traceback

        traceback.print_exc()


async def run_scheduler():
    """Run the scheduler with Redis-based schedule management"""
    # Initialize schedule from database and store in Redis
    print("Initializing schedule from database...")
    await initialize_schedule_from_db()

    # Start monitoring for schedule changes in background
    print("Starting schedule change monitoring...")
    monitor_task = asyncio.create_task(monitor_schedule_changes())

    try:
        # Run the scheduler — check pending jobs periodically
        while True:
            _debug("Scheduler running... checking for pending tasks.")
            for item in asyncio.all_tasks():
                _debug("Scheduled job:", item)
            for job in aioschedule.jobs:
                _debug("Job definition:", job)

            await aioschedule.run_pending()
            await asyncio.sleep(30)  # Check every 30 seconds
    finally:
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass


async def monitor_schedule_changes():
    """Monitor schedule changes in the background"""
    schedule_manager = await get_schedule_manager()
    await schedule_manager.monitor_schedule_changes()
