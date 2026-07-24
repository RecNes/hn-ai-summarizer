"""Worker tasks for processing stories with AI services"""

import asyncio
import json
import logging
import os

from arq.connections import RedisSettings
from sqlalchemy.future import select

# app.core.config already loads .env via Settings
from app.core.config import settings as app_settings
from app.core.database import AsyncSessionLocal
from app.models.activity_log import AiActivityLog
from app.models.preference import UserPreference
from app.models.setting import Setting
from app.models.story import Story
from app.services.ai_service import AIService
from app.services.fetcher import FetcherService
from app.services.story_service import StoryService
from app.shared.languages import TranslationLanguageResolver

logger = logging.getLogger(__name__)


# Set job timeout for AI processing (10 minutes)
job_timeout = 600  # 10 minutes in seconds

# Redis key for tracking model health status
REDIS_AI_HEALTH_KEY = "hn_reader:ai:health"
REDIS_WORKER_LOG_CHANNEL = "hn_reader:worker_log"
REDIS_WORKER_LOG_KEY = "hn_reader:worker_logs:recent"


def _format_processing_log(
    hn_id: str, db_id: int | None, title: str, status: str, duration_s: float | None = None,
    reason: str | None = None,
) -> str:
    """Format a consistent processing log entry."""
    parts = [f"● {status!r}"]
    if reason:
        parts.append(f"({reason})")
    parts.append(f" HN#{hn_id}")
    if db_id is not None:
        parts.append(f" DB#{db_id}")
    parts.append(f' "{title}"')
    if duration_s is not None:
        parts.append(f" {duration_s:.2f}s")
    return " ".join(parts)


async def _check_redis(conn) -> bool:
    """Check if Redis is accessible."""
    try:
        await conn.ping()
        return True
    except Exception:
        return False


async def _update_ai_health(ctx, is_healthy: bool):
    """Update AI health status in Redis for frontend polling.

    Called when all retries are exhausted (unhealthy) or when a call succeeds after being unhealthy.
    """
    import json as _json

    try:
        if await _check_redis(ctx["redis"]):
            await ctx["redis"].set(
                REDIS_AI_HEALTH_KEY,
                _json.dumps({
                    "healthy": is_healthy,
                    "timestamp": asyncio.get_event_loop().time(),
                }),
            )
    except Exception as e:
        logger.error("[AIHealth] Failed to update Redis: %s", e)


async def _get_ui_language(db) -> str:
    """Get user's UI language preference."""
    prefs_result = await db.execute(select(UserPreference).limit(1))
    prefs = prefs_result.scalar_one_or_none()
    return prefs.ui_language if prefs else "en"


async def _notify_ai_unreachable(ctx, language_code: str):
    """Send Telegram notification that AI model is unreachable."""
    from app.services.telegram_service import _get_locale_message, TelegramService

    bot_token = app_settings.TELEGRAM_BOT_TOKEN
    if not bot_token:
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Setting).limit(1))
        setting = result.scalar_one_or_none()

        if not setting or not setting.telegram_enabled or not setting.telegram_chat_id:
            return

        text = _get_locale_message("ai_unreachable", language_code)
        telegram = TelegramService(bot_token)
        await telegram.send_message(setting.telegram_chat_id, text)


async def _notify_ai_reachable(ctx, language_code: str):
    """Send Telegram notification that AI model is back online."""
    from app.services.telegram_service import _get_locale_message, TelegramService

    bot_token = app_settings.TELEGRAM_BOT_TOKEN
    if not bot_token:
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Setting).limit(1))
        setting = result.scalar_one_or_none()

        if not setting or not setting.telegram_enabled or not setting.telegram_chat_id:
            return

        text = _get_locale_message("ai_reachable", language_code)
        telegram = TelegramService(bot_token)
        await telegram.send_message(setting.telegram_chat_id, text)


async def _log_worker_event(
    db, event_type: str, story_id, hn_id: str, title: str,
    status: str, phase: str | None = None,
    error: str | None = None, error_code: str | None = None,
    trigger_source: str | None = None,
) -> dict:
    """Log a worker event to DB and return the log entry dict."""
    log = AiActivityLog(
        story_id=story_id,
        story_title=(title or "")[:200],
        event_type=event_type,
        provider="worker",
        model="",
        status=status,
        error_message=error,
        duration_ms=None,
        event_category="worker",
        worker_event_type=event_type,
        worker_status=status,
        worker_phase=phase,
        error_code=error_code,
        error_summary=error,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return {
        "id": log.id,
        "story_id": log.story_id,
        "story_title": log.story_title,
        "event_type": log.event_type,
        "event_category": "worker",
        "worker_event_type": log.worker_event_type,
        "worker_status": log.worker_status,
        "worker_phase": log.worker_phase,
        "status": log.status,
        "error_code": log.error_code,
        "error_summary": log.error_summary,
        "error_message": log.error_message,
        "created_at": log.created_at.isoformat(),
        "trigger_source": trigger_source,
    }


async def _publish_log_to_redis(ctx, log_data: dict):
    """Publish worker log to Redis Pub/Sub and keep recent list."""
    try:
        payload = json.dumps(log_data, default=str)
        await ctx["redis"].publish(REDIS_WORKER_LOG_CHANNEL, payload)
        await ctx["redis"].lpush(REDIS_WORKER_LOG_KEY, payload)
        await ctx["redis"].ltrim(REDIS_WORKER_LOG_KEY, 0, 19)
    except Exception as e:
        logger.warning("[WorkerLog] Failed to publish log to Redis: %s", e)


async def process_story(ctx, story_data):
    """Process a story with AI services"""
    hn_id = story_data.get("hacker_news_id", "?")
    title = story_data.get("title", "") or ""
    ai_service = AIService(story_id=hn_id)
    existing_story = None

    async with AsyncSessionLocal() as db:
        try:
            # Read user's translation language preference
            prefs_result = await db.execute(select(UserPreference).limit(1))
            prefs = prefs_result.scalar_one_or_none()
            target_lang_code = prefs.translation_language if prefs else "en"
            target_lang_name = TranslationLanguageResolver.get_language_name(target_lang_code)

            existing_story = await StoryService.get_by_hn_id(db, hn_id)

            if existing_story:
                db_id = existing_story.id
                if not existing_story.is_translated:
                    logger.info(
                        "Story HN#%s (DB#%s) exists but needs AI processing...",
                        hn_id, db_id,
                    )

                    title_tr = existing_story.title_tr
                    content_tr = existing_story.content_tr
                    comments_summary = existing_story.comments_summary

                    # Log start of reprocess
                    log_data = await _log_worker_event(
                        db, "story_reprocess", existing_story.id, hn_id, title,
                        "processing", "title",
                    )
                    await _publish_log_to_redis(ctx, log_data)

                    if not title_tr or title_tr.startswith("[TR]"):
                        title_tr = await ai_service.translate_title(
                            existing_story.title, target_lang_name
                        )
                        log_data = await _log_worker_event(
                            db, "story_reprocess", existing_story.id, hn_id, title,
                            "processing", "content",
                        )
                        await _publish_log_to_redis(ctx, log_data)

                    if not content_tr:
                        content_tr = await ai_service.summarize_content(
                            existing_story.content or "", target_lang_name
                        )
                        log_data = await _log_worker_event(
                            db, "story_reprocess", existing_story.id, hn_id, title,
                            "processing", "comments",
                        )
                        await _publish_log_to_redis(ctx, log_data)

                    if not comments_summary:
                        comments_summary = await ai_service.summarize_comments(
                            story_data.get("comments", []), target_lang_name
                        )

                    await StoryService.update_translations(
                        db, existing_story,
                        title_tr=title_tr,
                        content_tr=content_tr,
                        comments_summary=comments_summary,
                    )

                    # Check if AI is now reachable
                    if ai_service.had_connection_failure:
                        # Was previously unhealthy - now succeeded
                        await _update_ai_health(ctx, is_healthy=True)
                        ui_lang = await _get_ui_language(db)
                        await _notify_ai_reachable(ctx, ui_lang)

                    # Log success
                    log_data = await _log_worker_event(
                        db, "story_reprocess", existing_story.id, hn_id, title,
                        "success", None,
                    )
                    await _publish_log_to_redis(ctx, log_data)

                    logger.info(
                        _format_processing_log(
                            hn_id, db_id, title[:80], "ai_processed",
                            reason="existing_story",
                        )
                    )
                    return "ai_processed"
                else:
                    skip_reason = "already processed"
                    logger.info(
                        _format_processing_log(
                            hn_id, db_id, title[:80], "skipped", reason=skip_reason,
                        )
                    )
                    return "skipped"

            # Check if blocked by negative feedback
            is_blocked = await ai_service.check_negative_feedback(
                story_data.get("content", ""), story_data.get("title", "")
            )

            if is_blocked:
                logger.info(
                    _format_processing_log(
                        hn_id, None, title[:80], "skipped", reason="blocked",
                    )
                )
                return "skipped"

            # New story processing
            log_data = await _log_worker_event(
                db, "story_new", None, hn_id, title, "processing", "title",
            )
            await _publish_log_to_redis(ctx, log_data)

            title_tr = await ai_service.translate_title(
                story_data.get("title", ""), target_lang_name
            )

            log_data = await _log_worker_event(
                db, "story_new", None, hn_id, title, "processing", "content",
            )
            await _publish_log_to_redis(ctx, log_data)

            content_tr = await ai_service.summarize_content(
                story_data.get("content", ""), target_lang_name
            )

            log_data = await _log_worker_event(
                db, "story_new", None, hn_id, title, "processing", "comments",
            )
            await _publish_log_to_redis(ctx, log_data)

            comments_summary = await ai_service.summarize_comments(
                story_data.get("comments", []), target_lang_name
            )

            story_data_with_tr = dict(story_data)
            story_data_with_tr["title_tr"] = title_tr
            story_data_with_tr["content_tr"] = content_tr
            story_data_with_tr["comments_summary"] = comments_summary

            new_story = await StoryService.create(db, story_data_with_tr)
            new_db_id = new_story.id if hasattr(new_story, 'id') else None

            # Check health transition
            if ai_service.had_connection_failure:
                await _update_ai_health(ctx, is_healthy=True)
                ui_lang = await _get_ui_language(db)
                await _notify_ai_reachable(ctx, ui_lang)

            # Log success
            log_data = await _log_worker_event(
                db, "story_new", new_db_id, hn_id, title, "success", None,
            )
            await _publish_log_to_redis(ctx, log_data)

            logger.info(
                _format_processing_log(
                    hn_id, new_db_id, title[:80], "processed",
                )
            )
            return "processed"
        except Exception as e:
            error_msg = str(e)
            logger.error("Error processing story HN#%s: %s", hn_id, error_msg)

            # Determine error code
            error_code = "WORKER_ERROR"
            if ai_service:
                error_code = ai_service._determine_error_code(error_msg)
            if "fetch" in error_msg.lower() or "scrape" in error_msg.lower():
                error_code = "FETCH_ERROR"

            db_id = existing_story.id if existing_story else None
            log_data = await _log_worker_event(
                db, "story_new" if not existing_story else "story_reprocess",
                db_id, hn_id, title, "error", None,
                error=error_msg, error_code=error_code,
            )
            await _publish_log_to_redis(ctx, log_data)

            # Check if AI is now unhealthy
            if ai_service and ai_service.had_connection_failure:
                await _update_ai_health(ctx, is_healthy=False)
                ui_lang = await _get_ui_language(db)
                await _notify_ai_unreachable(ctx, ui_lang)

            # Enqueue retry for connection errors
            is_conn_error = any(
                kw in error_msg.lower()
                for kw in ["connection error", "connecterror", "temporary failure",
                           "name resolution", "api_connection_error"]
            )
            if is_conn_error and existing_story is None:
                # Not in DB yet - re-enqueue to retry after delay
                logger.info("  Will retry story HN#%s after delay...", hn_id)
                await ctx["redis"].enqueue_job(
                    "process_story", story_data,
                    _defer_until=asyncio.get_event_loop().time() + app_settings.AI_RETRY_INTERVAL,
                )

            return f"error: {error_msg}"


async def fetch_and_process_stories(ctx, send_notification: bool = True, trigger_source: str = "auto"):
    """Fetch and process stories from Hacker News

    Args:
        ctx: Arq worker context.
        send_notification: If True, sends Telegram notification after processing.
            Set to False when called manually via API trigger.
        trigger_source: "auto" for scheduler, "manual" for API trigger.
    """
    fetcher = FetcherService()

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Setting).limit(1))
        setting = result.scalar_one_or_none()
        min_score = setting.min_score if setting and setting.min_score else 100

    # Log worker triggered event
    async with AsyncSessionLocal() as db:
        log_data = await _log_worker_event(
            db, "worker_triggered", None, "", "fetch_new",
            "success", None,
            trigger_source=trigger_source,
        )
        await _publish_log_to_redis(ctx, log_data)

    stories = await fetcher.fetch_and_process_stories(min_score=min_score)

    # Re-enqueue failed stories to retry after delay
    for failed in fetcher.failed_stories:
        logger.info("  Re-enqueuing failed story HN#%s for retry...", failed['hacker_news_id'])
        try:
            await ctx["redis"].enqueue_job(
                "process_story", failed,
                _defer_until=asyncio.get_event_loop().time() + app_settings.AI_RETRY_INTERVAL,
            )
        except Exception as e:
            logger.error("  Failed to re-enqueue story HN#%s: %s", failed['hacker_news_id'], e)

    await fetcher.close()

    processed_count = 0
    skipped_count = 0
    error_count = 0

    for story in stories:
        try:
            result = await ctx["redis"].enqueue_job("process_story", story)
            if result:
                processed_count += 1
            else:
                skipped_count += 1
        except Exception as e:
            logger.error("Error enqueueing story %s: %s", story.get('hacker_news_id'), e)
            error_count += 1

    # Send Telegram notification if configured
    if send_notification:
        await _send_telegram_notification(processed_count, error_count)

    return f"New: {processed_count}, Skipped: {skipped_count}, Errors: {error_count}"


async def _send_telegram_notification(processed_count: int, error_count: int = 0):
    """Send Telegram notification about newly processed stories.

    Only sends if Telegram is configured in .env and settings.
    This is called only from scheduler-triggered fetches.
    """
    from app.core.config import settings as app_settings
    from app.services.telegram_service import TelegramService

    bot_token = app_settings.TELEGRAM_BOT_TOKEN
    if not bot_token:
        return  # Bot token not configured

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Setting).limit(1))
        setting = result.scalar_one_or_none()

        if not setting or not setting.telegram_enabled or not setting.telegram_chat_id:
            return  # Telegram not fully configured

        # Read user's UI language preference
        from app.models.preference import UserPreference
        prefs_result = await db.execute(select(UserPreference).limit(1))
        prefs = prefs_result.scalar_one_or_none()
        lang_code = prefs.ui_language if prefs else "en"

        telegram = TelegramService(bot_token)

        if processed_count > 0:
            await telegram.send_notification(
                processed_count, setting,
                error_count=error_count,
                language_code=lang_code,
            )
        else:
            await telegram.send_empty_notification(setting, language_code=lang_code)


async def reprocess_untranslated_stories(ctx):
    """Reprocess stories that don't have Turkish translations with fresh content"""
    fetcher = FetcherService()

    try:
        async with AsyncSessionLocal() as db:
            stories_needing_ai = await StoryService.get_untranslated(db)

            logger.info("Found %s stories needing AI processing", len(stories_needing_ai))

            reprocessed_count = 0
            for story in stories_needing_ai:
                if story.hacker_news_id is None:
                    logger.info("Skipping story DB id=%s: hacker_news_id is None", story.id)
                    continue

                hn_id = story.hacker_news_id
                ai_service = AIService(story_id=int(hn_id))
                try:
                    title_preview = (story.title or "")[:80]
                    logger.info(
                        "Reprocessing story HN#%s (DB#%s, \"%s\")...",
                        hn_id, story.id, title_preview,
                    )

                    log_data = await _log_worker_event(
                        db, "story_reprocess", story.id, hn_id, story.title or "",
                        "processing", "title",
                    )
                    await _publish_log_to_redis(ctx, log_data)

                    fresh_data = await fetcher.refetch_story_content(
                        int(hn_id), story.url or ""
                    )
                    if not fresh_data:
                        logger.error("Failed to refetch data for story HN#%s", hn_id)
                        log_data = await _log_worker_event(
                            db, "story_reprocess", story.id, hn_id, story.title or "",
                            "error", None, error="Failed to refetch data",
                            error_code="FETCH_ERROR",
                        )
                        await _publish_log_to_redis(ctx, log_data)
                        continue

                    await StoryService.update_from_fetch(db, story, fresh_data)

                    # Get target language from preferences
                    prefs_result = await db.execute(select(UserPreference).limit(1))
                    prefs = prefs_result.scalar_one_or_none()
                    target_lang_code = prefs.translation_language if prefs else "en"
                    target_lang_name = TranslationLanguageResolver.get_language_name(target_lang_code)

                    title_tr = await ai_service.translate_title(
                        fresh_data["title"], target_lang_name
                    )
                    log_data = await _log_worker_event(
                        db, "story_reprocess", story.id, hn_id, story.title or "",
                        "processing", "content",
                    )
                    await _publish_log_to_redis(ctx, log_data)

                    content_tr = await ai_service.summarize_content(
                        fresh_data["content"] or "", target_lang_name
                    )
                    log_data = await _log_worker_event(
                        db, "story_reprocess", story.id, hn_id, story.title or "",
                        "processing", "comments",
                    )
                    await _publish_log_to_redis(ctx, log_data)

                    comments_summary = await ai_service.summarize_comments(
                        fresh_data["comments"], target_lang_name
                    )

                    await StoryService.update_translations(
                        db, story,
                        title_tr=title_tr,
                        content_tr=content_tr,
                        comments_summary=comments_summary,
                    )
                    reprocessed_count += 1
                    logger.info("Successfully reprocessed story HN#%s (DB#%s)", hn_id, story.id)

                    log_data = await _log_worker_event(
                        db, "story_reprocess", story.id, hn_id, story.title or "",
                        "success", None,
                    )
                    await _publish_log_to_redis(ctx, log_data)

                except Exception as e:
                    error_msg = str(e)
                    logger.error("Error reprocessing story HN#%s: %s", hn_id, error_msg)
                    log_data = await _log_worker_event(
                        db, "story_reprocess", story.id, hn_id, story.title or "",
                        "error", None, error=error_msg,
                        error_code=ai_service._determine_error_code(error_msg),
                    )
                    await _publish_log_to_redis(ctx, log_data)

            return f"Reprocessed {reprocessed_count} stories with fresh content and AI processing"
    finally:
        await fetcher.close()


async def debug_untranslated_stories(ctx):
    """Debug function to check what stories need AI processing"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Story)
            .where((Story.is_translated.is_(None)) | (Story.is_translated == False))
            .order_by(Story.created_at.desc())
        )
        stories_needing_ai = result.scalars().all()

        debug_info = []
        for story in stories_needing_ai:
            debug_info.append({
                "id": story.id,
                "hacker_news_id": story.hacker_news_id,
                "title": story.title,
                "title_tr": story.title_tr,
                "content_tr_length": len(story.content_tr) if story.content_tr else 0,
                "comments_summary": story.comments_summary,
            })

        logger.info("DEBUG: Found %s stories needing AI processing", len(stories_needing_ai))
        for info in debug_info[:10]:
            logger.info(
                "  - Story %s: title_tr='%s', content_tr_len=%s, comments_summary='%s'",
                info['hacker_news_id'], info['title_tr'],
                info['content_tr_length'], info['comments_summary'],
            )

        return f"Found {len(stories_needing_ai)} stories needing AI processing"


async def reprocess_all_stories(ctx):
    """Reprocess ALL stories that might benefit from AI processing"""
    fetcher = FetcherService()

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Story).order_by(Story.created_at.desc()))
            all_stories = result.scalars().all()

            logger.info("Found %s total stories, checking each one...", len(all_stories))

            reprocessed_count = 0
            for story in all_stories:
                if story.hacker_news_id is None:
                    logger.info("Skipping story DB id=%s: hacker_news_id is None", story.id)
                    continue

                hn_id = story.hacker_news_id
                ai_service = AIService(story_id=int(hn_id))
                try:
                    if not story.is_translated:
                        logger.info("Reprocessing story HN#%s (DB#%s)...", hn_id, story.id)

                        log_data = await _log_worker_event(
                            db, "story_reprocess", story.id, hn_id, story.title or "",
                            "processing", "title",
                        )
                        await _publish_log_to_redis(ctx, log_data)

                        fresh_data = await fetcher.refetch_story_content(
                            int(hn_id), story.url or ""
                        )
                        if not fresh_data:
                            logger.error("Failed to refetch data for story HN#%s", hn_id)
                            continue

                        await StoryService.update_from_fetch(db, story, fresh_data)

                        # Get target language from preferences
                        prefs_result = await db.execute(select(UserPreference).limit(1))
                        prefs = prefs_result.scalar_one_or_none()
                        target_lang_code = prefs.translation_language if prefs else "en"
                        target_lang_name = TranslationLanguageResolver.get_language_name(target_lang_code)

                        title_tr = await ai_service.translate_title(
                            fresh_data["title"], target_lang_name
                        )
                        log_data = await _log_worker_event(
                            db, "story_reprocess", story.id, hn_id, story.title or "",
                            "processing", "content",
                        )
                        await _publish_log_to_redis(ctx, log_data)

                        content_tr = await ai_service.summarize_content(
                            fresh_data["content"] or "", target_lang_name
                        )
                        log_data = await _log_worker_event(
                            db, "story_reprocess", story.id, hn_id, story.title or "",
                            "processing", "comments",
                        )
                        await _publish_log_to_redis(ctx, log_data)

                        comments_summary = await ai_service.summarize_comments(
                            fresh_data["comments"], target_lang_name
                        )

                        await StoryService.update_translations(
                            db, story,
                            title_tr=title_tr,
                            content_tr=content_tr,
                            comments_summary=comments_summary,
                        )
                        reprocessed_count += 1
                        logger.info("Successfully reprocessed story HN#%s", hn_id)

                        log_data = await _log_worker_event(
                            db, "story_reprocess", story.id, hn_id, story.title or "",
                            "success", None,
                        )
                        await _publish_log_to_redis(ctx, log_data)
                    else:
                        logger.info("Story HN#%s is already fully processed", hn_id)

                except Exception as e:
                    error_msg = str(e)
                    logger.error("Error reprocessing story HN#%s: %s", hn_id, error_msg)
                    log_data = await _log_worker_event(
                        db, "story_reprocess", story.id, hn_id, story.title or "",
                        "error", None, error=error_msg,
                        error_code=ai_service._determine_error_code(error_msg),
                    )
                    await _publish_log_to_redis(ctx, log_data)

            return f"Reprocessed {reprocessed_count} stories with fresh content and AI processing"
    finally:
        await fetcher.close()


class WorkerSettings:
    """Settings for the ARQ worker."""

    functions = [
        process_story,
        fetch_and_process_stories,
        reprocess_untranslated_stories,
        debug_untranslated_stories,
        reprocess_all_stories,
    ]

    # Suppress Arq's verbose job logs (we use custom _format_processing_log instead)
    job_log_level = "WARNING"

    _redis_url = app_settings.REDIS_CONNECTION_URL
    if _redis_url:
        redis_settings = RedisSettings.from_dsn(_redis_url)
    else:
        rh = os.getenv("REDIS_HOST", "localhost")
        rp = int(os.getenv("REDIS_PORT", "6379"))
        rd = int(os.getenv("REDIS_DB", "0"))
        ru = os.getenv("REDIS_USERNAME", "") or None
        rpwd = os.getenv("REDIS_PASSWORD", "") or None
        redis_settings = RedisSettings(host=rh, port=rp, database=rd, username=ru, password=rpwd)

    max_jobs = 10
    job_timeout = job_timeout