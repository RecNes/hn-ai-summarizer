"""Worker tasks for processing stories with AI services"""

import os

from arq.connections import RedisSettings
from sqlalchemy.future import select

# app.core.config already loads .env via Settings
from app.core.config import settings as app_settings
from app.core.database import AsyncSessionLocal
from app.models.preference import UserPreference
from app.models.setting import Setting
from app.models.story import Story
from app.services.ai_service import AIService
from app.services.fetcher import FetcherService
from app.services.story_service import StoryService
from app.shared.languages import TranslationLanguageResolver


# Set job timeout for AI processing (10 minutes)
job_timeout = 600  # 10 minutes in seconds


async def process_story(ctx, story_data):
    """Process a story with AI services"""
    ai_service = AIService(story_id=story_data.get("hacker_news_id"))

    async with AsyncSessionLocal() as db:
        try:
            # Read user's translation language preference
            prefs_result = await db.execute(select(UserPreference).limit(1))
            prefs = prefs_result.scalar_one_or_none()
            target_lang_code = prefs.translation_language if prefs else "en"
            target_lang_name = TranslationLanguageResolver.get_language_name(target_lang_code)
            print(f"[Worker] Target translation language: {target_lang_name} ({target_lang_code})")

            existing_story = await StoryService.get_by_hn_id(
                db, story_data["hacker_news_id"]
            )

            if existing_story:
                if not existing_story.is_translated:
                    print(
                        f"Story {story_data['hacker_news_id']} exists but needs AI processing..."
                    )

                    title_tr = existing_story.title_tr
                    content_tr = existing_story.content_tr
                    comments_summary = existing_story.comments_summary

                    if not title_tr or title_tr.startswith("[TR]"):
                        title_tr = await ai_service.translate_title(
                            existing_story.title, target_lang_name
                        )

                    if not content_tr:
                        content_tr = await ai_service.summarize_content(
                            existing_story.content or "", target_lang_name
                        )

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
                    return "ai_processed"
                else:
                    print(f"Story {story_data['hacker_news_id']} already exists and is fully processed, skipping...")
                    return "skipped"

            is_blocked = await ai_service.check_negative_feedback(
                story_data.get("content", ""), story_data.get("title", "")
            )

            if is_blocked:
                print(f"Skipping blocked story: {story_data.get('title')}")
                return "skipped"

            title_tr = await ai_service.translate_title(story_data.get("title", ""), target_lang_name)
            content_tr = await ai_service.summarize_content(story_data.get("content", ""), target_lang_name)
            comments_summary = await ai_service.summarize_comments(story_data.get("comments", []), target_lang_name)

            story_data_with_tr = dict(story_data)
            story_data_with_tr["title_tr"] = title_tr
            story_data_with_tr["content_tr"] = content_tr
            story_data_with_tr["comments_summary"] = comments_summary

            await StoryService.create(db, story_data_with_tr)
            return "processed"
        except Exception as e:
            print(f"Error processing story {story_data.get('hacker_news_id')}: {e}")
            return f"error: {str(e)}"


async def fetch_and_process_stories(ctx, send_notification: bool = True):
    """Fetch and process stories from Hacker News

    Args:
        ctx: Arq worker context.
        send_notification: If True, sends Telegram notification after processing.
            Set to False when called manually via API trigger.
    """
    fetcher = FetcherService()

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Setting).limit(1))
        setting = result.scalar_one_or_none()
        min_score = setting.min_score if setting and setting.min_score else 100

    stories = await fetcher.fetch_and_process_stories(min_score=min_score)
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
            print(f"Error enqueueing story {story.get('hacker_news_id')}: {e}")
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

        telegram = TelegramService(bot_token)

        if processed_count > 0:
            await telegram.send_notification(processed_count, setting, error_count=error_count)
        else:
            await telegram.send_empty_notification(setting)


async def reprocess_untranslated_stories(ctx):
    """Reprocess stories that don't have Turkish translations with fresh content"""
    fetcher = FetcherService()

    try:
        async with AsyncSessionLocal() as db:
            stories_needing_ai = await StoryService.get_untranslated(db)

            print(f"Found {len(stories_needing_ai)} stories needing AI processing")

            reprocessed_count = 0
            for story in stories_needing_ai:
                ai_service = AIService(story_id=int(story.hacker_news_id))
                try:
                    print(f"Reprocessing story {story.hacker_news_id} (DB id={story.id}, title={story.title[:60]})...")

                    fresh_data = await fetcher.refetch_story_content(int(story.hacker_news_id), story.url)
                    if not fresh_data:
                        print(f"Failed to refetch data for story {story.hacker_news_id}")
                        continue

                    await StoryService.update_from_fetch(db, story, fresh_data)

                    title_tr = await ai_service.translate_title(fresh_data["title"])
                    content_tr = await ai_service.summarize_content(fresh_data["content"] or "")
                    comments_summary = await ai_service.summarize_comments(fresh_data["comments"])

                    await StoryService.update_translations(
                        db, story,
                        title_tr=title_tr,
                        content_tr=content_tr,
                        comments_summary=comments_summary,
                    )
                    reprocessed_count += 1
                    print(f"Successfully reprocessed story {story.hacker_news_id}")

                except Exception as e:
                    print(f"Error reprocessing story {story.hacker_news_id}: {e}")

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

        print(f"DEBUG: Found {len(stories_needing_ai)} stories needing AI processing")
        for info in debug_info[:10]:
            print(f"  - Story {info['hacker_news_id']}: title_tr='{info['title_tr']}',"
                  f"content_tr_len={info['content_tr_length']}, comments_summary='{info['comments_summary']}'")

        return f"Found {len(stories_needing_ai)} stories needing AI processing"


async def reprocess_all_stories(ctx):
    """Reprocess ALL stories that might benefit from AI processing"""
    fetcher = FetcherService()

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Story).order_by(Story.created_at.desc()))
            all_stories = result.scalars().all()

            print(f"Found {len(all_stories)} total stories, checking each one...")

            reprocessed_count = 0
            for story in all_stories:
                ai_service = AIService(story_id=int(story.hacker_news_id))
                try:
                    if not story.is_translated:
                        print(f"Reprocessing story {story.hacker_news_id}...")

                        fresh_data = await fetcher.refetch_story_content(int(story.hacker_news_id), story.url)
                        if not fresh_data:
                            print(f"Failed to refetch data for story {story.hacker_news_id}")
                            continue

                        await StoryService.update_from_fetch(db, story, fresh_data)

                        title_tr = await ai_service.translate_title(fresh_data["title"])
                        content_tr = await ai_service.summarize_content(fresh_data["content"] or "")
                        comments_summary = await ai_service.summarize_comments(fresh_data["comments"])

                        await StoryService.update_translations(
                            db, story,
                            title_tr=title_tr,
                            content_tr=content_tr,
                            comments_summary=comments_summary,
                        )
                        reprocessed_count += 1
                        print(f"Successfully reprocessed story {story.hacker_news_id}")
                    else:
                        print(f"Story {story.hacker_news_id} is already fully processed")

                except Exception as e:
                    print(f"Error reprocessing story {story.hacker_news_id}: {e}")

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