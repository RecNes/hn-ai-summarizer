"""Scheduler — timezone-aware, simple asyncio.sleep() based.

Reads schedule cron from Redis (fallback: DB), waits until the
next scheduled time, then enqueues a worker job via Arq.

Redis keys:
  hn_reader:schedule:config   → JSON {"cron_schedule": "..."}
  hn_reader:schedule:version  → integer string
"""

from __future__ import annotations

import asyncio
import json
import logging
import zoneinfo
from datetime import datetime, timedelta, timezone as dt_timezone

from arq import create_pool
from arq.connections import RedisSettings
from sqlalchemy.future import select

from app.core.config import settings as app_settings
from app.core.database import AsyncSessionLocal
from app.models.activity_log import AiActivityLog
from app.models.setting import Setting

logger = logging.getLogger(__name__)

# ── Redis keys ──────────────────────────
SCHEDULE_KEY = "hn_reader:schedule:config"
VERSION_KEY = "hn_reader:schedule:version"

# ── Cron parser helpers ─────────────────


def _parse_cron_time(cron: str) -> tuple[int, int] | None:
    """Parse hour & minute from a 5-field cron string.  Returns (hour, minute) or None."""
    parts = cron.strip().split()
    if len(parts) != 5:
        return None
    try:
        return int(parts[1]), int(parts[0])  # hour, minute
    except ValueError:
        return None


def _parse_cron_days(cron: str) -> list[int]:
    """Return list of cron weekdays (0=Sunday..6=Saturday) from the 5th field."""
    parts = cron.strip().split()
    if len(parts) != 5:
        return []
    field = parts[4]
    if field == "*":
        return []
    days: list[int] = []
    for chunk in field.split(","):
        chunk = chunk.strip()
        if "-" in chunk:
            try:
                a, b = map(int, chunk.split("-", 1))
                days.extend(range(a, b + 1))
            except ValueError:
                pass
        else:
            try:
                days.append(int(chunk))
            except ValueError:
                pass
    return days


# ── Timezone helper ─────────────────────


def _get_tz() -> zoneinfo.ZoneInfo:
    """Return the configured timezone, falling back to UTC."""
    name = (app_settings.TIMEZONE or "").strip()
    if name:
        try:
            return zoneinfo.ZoneInfo(name)
        except (zoneinfo.ZoneInfoNotFoundError, KeyError):
            logger.warning(
                "[SCHEDULER] Unknown timezone '%s', falling back to UTC", name
            )
    return zoneinfo.ZoneInfo("UTC")


# ── Next-run calculation ────────────────


def _calculate_next_run(
    cron: str, tz: zoneinfo.ZoneInfo, now: datetime | None = None
) -> datetime:
    """Return the *next* aware datetime (in the given tz) a job should fire.

    - If today matches and the time hasn't passed yet → return today's datetime.
    - If today matches but the time has passed → advance to next matching day.
    - If no days configured → run *every day* at the given time.
    """
    parsed = _parse_cron_time(cron)
    if parsed is None:
        # Invalid cron → default to tomorrow 09:00
        if now is None:
            now = datetime.now(tz)
        return now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(
            days=1
        )

    target_hour, target_minute = parsed
    days = _parse_cron_days(cron)  # empty list = every day

    if now is None:
        now = datetime.now(tz)

    # Start from today at target time
    candidate = now.replace(
        hour=target_hour, minute=target_minute, second=0, microsecond=0
    )

    # If time hasn't passed yet AND (no day filter OR today is selected)
    if days:
        # cron weekday: 0=Sunday → Python weekday: 0=Monday
        today_cron = (now.weekday() + 1) % 7
        if today_cron in days and candidate > now:
            return candidate
    else:
        if candidate > now:
            return candidate

    # Either time has passed today or today isn't a selected day.
    # Walk forward day by day until we find a match.
    for _ in range(8):  # safety net — max 7 days
        candidate += timedelta(days=1)
        if days:
            cand_cron = (candidate.weekday() + 1) % 7
            if cand_cron in days:
                return candidate
        else:
            return candidate

    # Should never reach here
    return candidate


# ── Redis helpers ───────────────────────


async def _get_redis_pool():
    """Create a short-lived Redis connection pool."""
    url = app_settings.REDIS_CONNECTION_URL or "redis://localhost:6379/0"
    return await create_pool(RedisSettings.from_dsn(url))


async def _get_schedule_from_redis() -> dict | None:
    """Read schedule config from Redis."""
    pool = await _get_redis_pool()
    try:
        data = await pool.get(SCHEDULE_KEY)  # type: ignore[union-attr]
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        logger.warning("[SCHEDULER] Redis read error: %s", e)
        return None
    finally:
        await pool.aclose()


async def _get_schedule_version() -> str:
    """Return current schedule version from Redis."""
    pool = await _get_redis_pool()
    try:
        v = await pool.get(VERSION_KEY)  # type: ignore[union-attr]
        return v or "0"
    except Exception:
        return "0"
    finally:
        await pool.aclose()


async def _write_schedule_to_redis(cron: str):
    """Write schedule config + bump version in Redis."""
    pool = await _get_redis_pool()
    try:
        await pool.set(  # type: ignore[union-attr]
            SCHEDULE_KEY, json.dumps({"cron_schedule": cron})
        )
        v = await pool.get(VERSION_KEY)  # type: ignore[union-attr]
        new_v = str(int(v) + 1 if v else 1)
        await pool.set(VERSION_KEY, new_v)  # type: ignore[union-attr]
        logger.debug("[SCHEDULER] Redis schedule written (version=%s)", new_v)
    finally:
        await pool.aclose()


# ── DB helpers ──────────────────────────


async def _get_schedule_from_db() -> str:
    """Read cron_schedule from the settings table."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Setting).limit(1))
        setting = result.scalar_one_or_none()
        await db.commit()
        return setting.cron_schedule if setting and setting.cron_schedule else "0 9 * * *"


# ── Worker enqueue ──────────────────────


async def _enqueue_worker_job() -> bool:
    """Enqueue a fetch_and_process_stories job. Returns True on success."""
    pool = await _get_redis_pool()
    try:
        job = await pool.enqueue_job("fetch_and_process_stories")  # type: ignore[union-attr]
        if job:
            logger.info(
                "[SCHEDULER] ✅ Worker job enqueued — job_id=%s", job.job_id
            )
            return True
        else:
            logger.warning("[SCHEDULER] ❌ Enqueue returned None (queue full?)")
            return False
    except Exception as e:
        logger.error("[SCHEDULER] ❌ Failed to enqueue job: %s", e)
        return False
    finally:
        await pool.aclose()


# ── Cleanup ─────────────────────────────


async def _cleanup_old_logs():
    """Delete AiActivityLog records older than 30 days."""
    cutoff = datetime.now(dt_timezone.utc) - timedelta(days=30)
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(AiActivityLog).where(AiActivityLog.created_at < cutoff)
            )
            old = result.scalars().all()
            for log in old:
                await db.delete(log)
            await db.commit()
            if old:
                logger.info("[SCHEDULER] Cleaned up %d old activity logs", len(old))
    except Exception as e:
        logger.error("[SCHEDULER] Cleanup error: %s", e)


# ── Main scheduler loop ─────────────────


async def run_scheduler():
    """Main entry point — runs forever, sleeping until the next job time."""
    tz = _get_tz()
    tz_name = str(tz)
    logger.info("[SCHEDULER] ▶ STARTED — timezone=%s", tz_name)

    # ── Load initial schedule ────────────
    # Prefer Redis; fall back to DB → write to Redis
    redis_config = await _get_schedule_from_redis()
    if redis_config and redis_config.get("cron_schedule"):
        cron = redis_config["cron_schedule"]
        logger.info("[SCHEDULER] Loaded schedule from Redis: %s", cron)
    else:
        cron = await _get_schedule_from_db()
        logger.info("[SCHEDULER] Loaded schedule from DB: %s", cron)
        await _write_schedule_to_redis(cron)

    current_version = await _get_schedule_version()

    # ── Initial next-run calculation ─────
    next_run = _calculate_next_run(cron, tz)
    _log_next_run(next_run, cron)

    # ── Clean up old logs ────────────────
    await _cleanup_old_logs()

    # ── Main loop ────────────────────────
    while True:
        try:
            now = datetime.now(tz)
            sleep_seconds = max(0, (next_run - now).total_seconds())

            if sleep_seconds > 0:
                # Sleep in 30-second chunks so we can check for schedule updates
                while sleep_seconds > 30:
                    await asyncio.sleep(30)
                    sleep_seconds -= 30

                    # Check for schedule version change
                    ver = await _get_schedule_version()
                    if ver != current_version:
                        logger.info(
                            "[SCHEDULER] Version changed: %s → %s, reloading",
                            current_version,
                            ver,
                        )
                        cfg = await _get_schedule_from_redis()
                        if cfg and cfg.get("cron_schedule"):
                            cron = cfg["cron_schedule"]
                        else:
                            cron = await _get_schedule_from_db()
                        current_version = ver
                        new_next = _calculate_next_run(cron, tz, now=now)
                        if new_next != next_run:
                            logger.info(
                                "[SCHEDULER] Schedule updated! New cron='%s'", cron
                            )
                            next_run = new_next
                            _log_next_run(next_run, cron)
                            # Break out of inner loop to restart the outer sleep
                            break

                # If next_run was updated, skip the remaining sleep & recalc
                now = datetime.now(tz)
                sleep_seconds = max(0, (next_run - now).total_seconds())
                if sleep_seconds > 0:
                    await asyncio.sleep(sleep_seconds)

            # ── Time to run! ───────────────
            now_str = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
            logger.info(
                "[SCHEDULER] ⏰ TRIGGERED at %s %s (cron='%s')",
                now_str,
                tz_name,
                cron,
            )
            success = await _enqueue_worker_job()

            # ── Schedule next run ───────────
            now = datetime.now(tz)
            next_run = _calculate_next_run(cron, tz, now=now)
            _log_next_run(next_run, cron)

            # Periodic cleanup
            if now.hour == 3 and now.minute < 5:
                await _cleanup_old_logs()

        except asyncio.CancelledError:
            logger.info("[SCHEDULER] Cancelled, shutting down")
            break
        except Exception as e:
            logger.error("[SCHEDULER] Unexpected error in main loop: %s", e, exc_info=True)
            await asyncio.sleep(30)


def _log_next_run(next_run: datetime, cron: str):
    """Log the next scheduled run time."""
    delta = next_run - datetime.now(next_run.tzinfo)
    hours, rem = divmod(int(delta.total_seconds()), 3600)
    minutes = rem // 60
    logger.info(
        "[SCHEDULER] 📅 Next run: %s (in %dh %dm) | cron='%s'",
        next_run.strftime("%Y-%m-%d %H:%M:%S %Z"),
        hours,
        minutes,
        cron,
    )