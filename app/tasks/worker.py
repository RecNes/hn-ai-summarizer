"""Worker tasks for processing stories with AI services"""

import os

from arq.connections import RedisSettings
from sqlalchemy.future import select

import os
from pathlib import Path

from dotenv import load_dotenv
# Always resolve .env relative to project root
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(str(_env_path))

from app.core.config import settings as app_settings
from app.core.database import AsyncSessionLocal
from app.models.setting import Setting
from app.models.story import Story
from app.services.ai_service import AIService
from app.services.fetcher import FetcherService


redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", "6379"))
redis_db = int(os.getenv("REDIS_DB", "0"))

# Use REDIS_CONNECTION_URL from config (reads from .env)
redis_url = app_settings.REDIS_CONNECTION_URL
if redis_url:
    redis_settings = RedisSettings.from_dsn(redis_url)
else:
    redis_settings = RedisSettings(host=redis_host, port=redis_port, database=redis_db)

# Set job timeout for AI processing (10 minutes)
job_timeout = 600  # 10 minutes in seconds


async def process_story(ctx, story_data):
    """Process a story with AI services"""

    async with AsyncSessionLocal() as db:
        try:
            # Check if story already exists
            from sqlalchemy.future import select

            result = await db.execute(
                select(Story).where(
                    Story.hacker_news_id == story_data["hacker_news_id"]
                )
            )
            existing_story = result.scalar_one_or_none()

            if existing_story:
                # Check if story needs AI processing (missing Turkish translations)
                needs_ai_processing = (
                    not existing_story.title_tr
                    or not existing_story.content_tr
                    or not existing_story.comments_summary
                    or (
                        existing_story.title_tr
                        and existing_story.title_tr.startswith("[TR]")
                    )
                )

                if needs_ai_processing:
                    print(
                        f"Story {story_data['hacker_news_id']} exists but needs AI processing..."
                    )
                    # Process with AI services
                    ai_service = AIService()

                    # Process title translation if needed
                    if not existing_story.title_tr or (
                        existing_story.title_tr
                        and existing_story.title_tr.startswith("[TR]")
                    ):
                        title_tr = await ai_service.translate_title(
                            existing_story.title
                        )
                        existing_story.title_tr = title_tr

                    # Process content summary if needed
                    if not existing_story.content_tr:
                        content_tr = await ai_service.summarize_content(
                            existing_story.content or ""
                        )
                        existing_story.content_tr = content_tr

                    # Process comments summary if needed
                    if not existing_story.comments_summary:
                        comments_summary = await ai_service.summarize_comments([])
                        existing_story.comments_summary = comments_summary

                    await db.commit()
                    return "ai_processed"
                else:
                    print(
                        f"Story {story_data['hacker_news_id']} already exists and is fully processed, skipping..."
                    )
                    return "skipped"

            # Check negative feedback first
            ai_service = AIService()
            is_blocked = await ai_service.check_negative_feedback(
                story_data.get("content", ""), story_data.get("title", "")
            )

            if is_blocked:
                print(f"Skipping blocked story: {story_data.get('title')}")
                return "skipped"

            # Process with AI services
            title_tr = await ai_service.translate_title(story_data.get("title", ""))
            content_tr = await ai_service.summarize_content(
                story_data.get("content", "")
            )
            comments_summary = await ai_service.summarize_comments(
                story_data.get("comments", [])
            )

            # Save to database
            story = Story(
                hacker_news_id=story_data["hacker_news_id"],
                title=story_data["title"],
                title_tr=title_tr,
                url=story_data["url"],
                score=story_data["score"],
                author=story_data["author"],
                content=story_data["content"],
                content_tr=content_tr,
                comments_summary=comments_summary,
                is_blocked=False,
            )

            db.add(story)
            await db.commit()

            return "processed"
        except Exception as e:
            await db.rollback()
            print(f"Error processing story {story_data.get('hacker_news_id')}: {e}")
            return f"error: {str(e)}"


async def fetch_and_process_stories(ctx):
    """Fetch and process stories from Hacker News"""
    fetcher = FetcherService()

    # Get settings
    async with AsyncSessionLocal() as db:
        """Get minimum score setting"""

        result = await db.execute(select(Setting).limit(1))
        setting = result.scalar_one_or_none()
        min_score = setting.min_score if setting and setting.min_score else 100

    # Fetch stories
    stories = await fetcher.fetch_and_process_stories(min_score=min_score)

    # Process each story
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

    return f"New: {processed_count}, Skipped: {skipped_count}, Errors: {error_count}"


async def reprocess_untranslated_stories(ctx):
    """Reprocess stories that don't have Turkish translations with fresh content"""
    fetcher = FetcherService()
    ai_service = AIService()

    async with AsyncSessionLocal() as db:
        # Find stories that need AI processing - more comprehensive query
        result = await db.execute(
            select(Story)
            .where(
                (Story.title_tr.is_(None))
                | (Story.title_tr.like("[TR]%"))
                | (Story.content_tr.is_(None))
                | (Story.content_tr == "")
                | (Story.comments_summary.is_(None))
                | (Story.comments_summary == "")
                | (Story.comments_summary == "Yorum özeti mevcut değil.")
            )
            .order_by(Story.created_at.desc())
        )
        stories_needing_ai = result.scalars().all()

        print(f"Found {len(stories_needing_ai)} stories needing AI processing")

        reprocessed_count = 0
        for story in stories_needing_ai:
            try:
                print(f"Reprocessing story {story.hacker_news_id} (DB id={story.id}, title={story.title[:60]})...")

                # Refetch fresh content and comments
                fresh_data = await fetcher.refetch_story_content(
                    int(story.hacker_news_id), story.url
                )

                if not fresh_data:
                    print(f"Failed to refetch data for story {story.hacker_news_id}")
                    continue

                # Process with AI services using fresh data
                title_tr = await ai_service.translate_title(fresh_data["title"])
                content_tr = await ai_service.summarize_content(
                    fresh_data["content"] or ""
                )
                comments_summary = await ai_service.summarize_comments(
                    fresh_data["comments"]
                )

                # Update the story with fresh AI processing
                story.title_tr = title_tr
                story.content_tr = content_tr
                story.comments_summary = comments_summary

                await db.commit()
                reprocessed_count += 1
                print(f"Successfully reprocessed story {story.hacker_news_id}")

            except Exception as e:
                await db.rollback()
                print(f"Error reprocessing story {story.hacker_news_id}: {e}")

        return f"Reprocessed {reprocessed_count} stories with fresh content and AI processing"


# Add this function to the worker.py file
async def debug_untranslated_stories(ctx):
    """Debug function to check what stories need AI processing"""
    async with AsyncSessionLocal() as db:
        # Find stories that need AI processing - comprehensive query
        result = await db.execute(
            select(Story)
            .where(
                (Story.title_tr.is_(None))
                | (Story.title_tr.like("[TR]%"))
                | (Story.content_tr.is_(None))
                | (Story.content_tr == "")
                | (Story.comments_summary.is_(None))
                | (Story.comments_summary == "")
                | (Story.comments_summary == "Yorum özeti mevcut değil.")
            )
            .order_by(Story.created_at.desc())
        )
        stories_needing_ai = result.scalars().all()

        debug_info = []
        for story in stories_needing_ai:
            debug_info.append(
                {
                    "id": story.id,
                    "hacker_news_id": story.hacker_news_id,
                    "title": story.title,
                    "title_tr": story.title_tr,
                    "content_tr_length": (
                        len(story.content_tr) if story.content_tr else 0
                    ),
                    "comments_summary": story.comments_summary,
                }
            )

        print(f"DEBUG: Found {len(stories_needing_ai)} stories needing AI processing")
        for info in debug_info[:10]:  # Show first 10
            print(
                f"  - Story {info['hacker_news_id']}: title_tr='{info['title_tr']}',",
                f"content_tr_len={info['content_tr_length']}, comments_summary='{info['comments_summary']}'"
            )

        return f"Found {len(stories_needing_ai)} stories needing AI processing"


# Add this function to worker.py
async def reprocess_all_stories(ctx):
    """Reprocess ALL stories that might benefit from AI processing"""
    fetcher = FetcherService()
    ai_service = AIService()

    async with AsyncSessionLocal() as db:
        # Find ALL stories (more aggressive approach)
        result = await db.execute(select(Story).order_by(Story.created_at.desc()))
        all_stories = result.scalars().all()

        print(f"Found {len(all_stories)} total stories, checking each one...")

        reprocessed_count = 0
        for story in all_stories:
            try:
                # Check if this story needs any AI processing
                needs_processing = (
                    not story.title_tr
                    or (story.title_tr and story.title_tr.startswith("[TR]"))
                    or not story.content_tr
                    or story.content_tr == ""
                    or not story.comments_summary
                    or story.comments_summary == ""
                    or story.comments_summary == "Yorum özeti mevcut değil."
                )

                if needs_processing:
                    print(f"Reprocessing story {story.hacker_news_id}...")

                    # Refetch fresh content and comments
                    fresh_data = await fetcher.refetch_story_content(
                        int(story.hacker_news_id), story.url
                    )

                    if not fresh_data:
                        print(
                            f"Failed to refetch data for story {story.hacker_news_id}"
                        )
                        continue

                    # Process with AI services using fresh data
                    title_tr = await ai_service.translate_title(fresh_data["title"])
                    content_tr = await ai_service.summarize_content(
                        fresh_data["content"] or ""
                    )
                    comments_summary = await ai_service.summarize_comments(
                        fresh_data["comments"]
                    )

                    # Update the story with fresh AI processing
                    story.title_tr = title_tr
                    story.content_tr = content_tr
                    story.comments_summary = comments_summary

                    await db.commit()
                    reprocessed_count += 1
                    print(f"Successfully reprocessed story {story.hacker_news_id}")
                else:
                    print(f"Story {story.hacker_news_id} is already fully processed")

            except Exception as e:
                await db.rollback()
                print(f"Error reprocessing story {story.hacker_news_id}: {e}")

        return f"Reprocessed {reprocessed_count} stories with fresh content and AI processing"


# Update WorkerSettings to include the new function
class WorkerSettings:
    """Settings for the ARQ worker."""

    functions = [
        process_story,
        fetch_and_process_stories,
        reprocess_untranslated_stories,
        debug_untranslated_stories,
        reprocess_all_stories,
    ]

    # Redis settings — resolved from config.py (reads .env)
    _redis_url = app_settings.REDIS_CONNECTION_URL
    if _redis_url:
        redis_settings = RedisSettings.from_dsn(_redis_url)
    else:
        rh = os.getenv("REDIS_HOST", "localhost")
        rp = int(os.getenv("REDIS_PORT", "6379"))
        rd = int(os.getenv("REDIS_DB", "0"))
        redis_settings = RedisSettings(host=rh, port=rp, database=rd)

    max_jobs = 10
    job_timeout = job_timeout  # 10 minutes for AI processing jobs
