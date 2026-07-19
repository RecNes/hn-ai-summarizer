"""API routes for managing stories."""

import json
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.models.story import Story
from app.schemas.story import StoryResponse
from app.services.ai_service import AIService
from app.services.fetcher import FetcherService

router = APIRouter()


async def _reprocess_ai(story_id: int, db: AsyncSession):
    """Background task: run AI translation/summarization after HN data is fetched."""
    try:
        result = await db.execute(select(Story).where(Story.id == story_id))
        story = result.scalar_one_or_none()
        if not story:
            return

        hn_id = story.hacker_news_id
        if not hn_id:
            return

        # Refetch fresh data (already done in main request, but redo for simplicity)
        fetcher = FetcherService()
        fresh_data = await fetcher.refetch_story_content(int(hn_id), story.url or "")
        if not fresh_data or not fresh_data.get("title"):
            return

        ai_service = AIService()
        title_tr = await ai_service.translate_title(fresh_data["title"])
        content_tr = await ai_service.summarize_content(fresh_data.get("content", ""))
        comments_summary = await ai_service.summarize_comments(fresh_data.get("comments", []))

        story.title = fresh_data.get("title", story.title)
        story.title_tr = title_tr
        story.url = fresh_data.get("url", story.url)
        story.score = fresh_data.get("score", story.score)
        story.author = fresh_data.get("author", story.author)
        story.content = fresh_data.get("content", story.content)
        story.content_tr = content_tr
        story.comments_summary = comments_summary
        story.is_blocked = False

        await db.commit()
        print(f"[Background] Successfully reprocessed story {story_id} (HN={hn_id})")
    except Exception as e:
        print(f"[Background] Error reprocessing story {story_id}: {e}")
    finally:
        await db.close()


@router.get("/", response_model=List[StoryResponse])
async def get_stories(
    skip: int = 0, limit: int = 20, db: AsyncSession = Depends(get_db)
):
    """Get all stories with pagination"""
    result = await db.execute(
        select(Story).order_by(Story.created_at.desc()).offset(skip).limit(limit)
    )
    stories = result.scalars().all()
    return stories


@router.get("/reprocess-untranslated/stream")
async def reprocess_untranslated_stream(request: Request):
    """SSE endpoint: reprocess untranslated stories with live progress updates.

    Streams events:
      - progress: {"current": N, "total": M, "percentage": X, "story_id": ID}
      - story_update: {"id": ID, "title_tr": "...", ...}
      - complete: {"message": "Done", "total": M, "processed": N, "errors": E}
      - error: {"detail": "..."}
    """
    from app.core.database import AsyncSessionLocal
    from app.models.preference import UserPreference
    from app.shared.languages import TranslationLanguageResolver

    async def event_stream():
        fetcher = FetcherService()
        try:
            async with AsyncSessionLocal() as db:
                # Find untranslated stories
                result = await db.execute(
                    select(Story)
                    .where((Story.is_translated.is_(None)) | (Story.is_translated == False))
                    .order_by(Story.created_at.desc())
                )
                stories = result.scalars().all()

                # Read language preference
                prefs_result = await db.execute(
                    select(UserPreference).limit(1)
                )
                prefs = prefs_result.scalar_one_or_none()
                target_lang_code = prefs.translation_language if prefs else "en"
                target_lang_name = TranslationLanguageResolver.get_language_name(target_lang_code)

                total = len(stories)
                yield f"event: progress\ndata: {json.dumps({'current': 0, 'total': total, 'percentage': 0})}\n\n"

                processed = 0
                errors = 0

                for idx, story in enumerate(stories, 1):
                    # Check if client disconnected
                    if await request.is_disconnected():
                        break

                    try:
                        hn_id = int(story.hacker_news_id)
                        ai_service = AIService(story_id=hn_id)

                        fresh_data = await fetcher.refetch_story_content(hn_id, story.url or "")
                        if not fresh_data:
                            errors += 1
                            continue

                        title_tr = await ai_service.translate_title(fresh_data["title"], target_lang_name)
                        content_tr = await ai_service.summarize_content(fresh_data.get("content", ""), target_lang_name)
                        comments_summary = await ai_service.summarize_comments(fresh_data.get("comments", []), target_lang_name)

                        story.title_tr = title_tr
                        story.content_tr = content_tr
                        story.comments_summary = comments_summary
                        story.is_translated = ai_service.check_translation_complete(story)
                        await db.commit()
                        await db.refresh(story)

                        processed += 1

                        # Send progress
                        pct = round((idx / total) * 100) if total > 0 else 100
                        yield f"event: progress\ndata: {json.dumps({'current': idx, 'total': total, 'percentage': pct, 'story_id': story.id})}\n\n"

                        # Send story update for live card refresh
                        story_data = {
                            "id": story.id,
                            "hacker_news_id": story.hacker_news_id,
                            "title": story.title,
                            "title_tr": story.title_tr,
                            "url": story.url,
                            "score": story.score,
                            "author": story.author,
                            "content_tr": story.content_tr,
                            "comments_summary": story.comments_summary,
                            "is_translated": story.is_translated,
                            "is_read": story.is_read,
                            "hn_created_at": story.hn_created_at.isoformat() if story.hn_created_at else None,
                            "created_at": story.created_at.isoformat() if story.created_at else None,
                        }
                        yield f"event: story_update\ndata: {json.dumps(story_data)}\n\n"

                    except Exception as e:
                        errors += 1
                        print(f"[SSE] Error reprocessing story {story.id}: {e}")

                yield f"event: complete\ndata: {json.dumps({'message': 'Done', 'total': total, 'processed': processed, 'errors': errors})}\n\n"

        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"
        finally:
            await fetcher.close()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{story_id}", response_model=StoryResponse)
async def get_story(story_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific story by ID"""
    result = await db.execute(select(Story).where(Story.id == story_id))
    story = result.scalar_one_or_none()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story


@router.post("/{story_id}/reprocess")
async def reprocess_story(
    story_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Reprocess a single story: refetch from HN, re-translate, re-summarize

    HN data is fetched synchronously (fast), AI processing runs in background.
    """
    result = await db.execute(select(Story).where(Story.id == story_id))
    story = result.scalar_one_or_none()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    hn_id = story.hacker_news_id
    if not hn_id:
        raise HTTPException(status_code=400, detail="Story has no HN id")

    # Get fresh data from HN (fast network operation)
    fetcher = FetcherService()
    fresh_data = await fetcher.refetch_story_content(int(hn_id), story.url or "")
    if not fresh_data or not fresh_data.get("title"):
        raise HTTPException(status_code=500, detail="Failed to refetch story from HN")

    # Update DB with fresh HN data immediately
    story.title = fresh_data.get("title", story.title)
    story.url = fresh_data.get("url", story.url)
    story.score = fresh_data.get("score", story.score)
    story.author = fresh_data.get("author", story.author)
    story.content = fresh_data.get("content", story.content)
    await db.commit()

    # Schedule AI processing in background (won't block the response)
    # We need to get a fresh session for the background task
    from app.core.database import AsyncSessionLocal

    async def _run_ai():
        async with AsyncSessionLocal() as bg_db:
            await _reprocess_ai(story_id, bg_db)

    background_tasks.add_task(_run_ai)

    return {
        "message": "Story reprocessing started. AI translation runs in background (refresh page after ~30s).",
        "id": story.id,
        "fresh_data_fetched": True,
    }


@router.patch("/{story_id}/read")
async def toggle_read_story(story_id: int, db: AsyncSession = Depends(get_db)):
    """Toggle the is_read status of a story"""
    result = await db.execute(select(Story).where(Story.id == story_id))
    story = result.scalar_one_or_none()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    story.is_read = not story.is_read
    await db.commit()
    await db.refresh(story)
    return {"id": story.id, "is_read": story.is_read}


@router.post("/feedback/negative/{story_id}")
async def add_negative_feedback(story_id: int, db: AsyncSession = Depends(get_db)):
    """Add negative feedback for a story"""
    result = await db.execute(select(Story).where(Story.id == story_id))
    story = result.scalar_one_or_none()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    story.is_blocked = True
    await db.commit()
    return {"message": "Negative feedback recorded"}