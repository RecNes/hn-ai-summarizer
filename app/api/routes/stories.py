"""API routes for managing stories."""

import asyncio
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

# ── Shared SSE helpers ──────────────────────


async def _sse_event(event_type: str, data: dict) -> str:
    """Format an SSE event string."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


def _story_to_dict(story) -> dict:
    """Convert a Story ORM object to a plain dict for SSE."""
    return {
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


# ── Background AI reprocess ──────────────────


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


# ── Routes ──────────────────────────────────


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


@router.get("/reprocess-untranslated/status")
async def reprocess_untranslated_status():
    """Return current reprocess job state (Redis-backed, survives server restart)."""
    from app.services.reprocess_state import get_reprocess_state
    return await get_reprocess_state()


@router.post("/reprocess-untranslated/cancel")
async def cancel_reprocess():
    """Cancel the currently running reprocess job by resetting Redis state."""
    from app.services.reprocess_state import reset_reprocess_state

    await reset_reprocess_state()
    return {"message": "Reprocess cancelled"}


@router.get("/poll-stream")
async def story_poll_stream(request: Request):
    """SSE endpoint: streams new stories as they arrive."""
    from app.core.database import AsyncSessionLocal

    async def event_stream():
        last_max_id = 0
        keepalive_counter = 0

        try:
            while True:
                if await request.is_disconnected():
                    break

                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        select(Story)
                        .order_by(Story.id.desc())
                        .limit(5)
                    )
                    stories = result.scalars().all()

                if stories:
                    current_max_id = max(s.id for s in stories)
                    if last_max_id == 0:
                        last_max_id = current_max_id
                    elif current_max_id > last_max_id:
                        new_ones = [s for s in stories if s.id > last_max_id]
                        new_ones.sort(key=lambda s: s.id)
                        for story in new_ones:
                            yield await _sse_event("story_update", _story_to_dict(story))
                        last_max_id = current_max_id
                    elif current_max_id == last_max_id:
                        keepalive_counter += 1
                        if keepalive_counter >= 10:
                            yield await _sse_event("keepalive", {})
                            keepalive_counter = 0

                await asyncio.sleep(3)

        except asyncio.CancelledError:
            pass
        finally:
            print("[SSE/poll-stream] Client disconnected")

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/reprocess-untranslated/stream")
async def reprocess_untranslated_stream(request: Request):
    """SSE endpoint: reprocess untranslated stories with live progress updates.

    Only one reprocess stream is allowed at a time.
    If another stream is already running, returns 409 Conflict.
    Checks Redis 'cancelled' flag before each story; exits early if set.
    """
    from app.core.database import AsyncSessionLocal
    from app.models.preference import UserPreference
    from app.services.reprocess_state import get_reprocess_state, reset_reprocess_state, set_reprocess_state
    from app.shared.languages import TranslationLanguageResolver

    # Check if a reprocess is already running
    current_state = await get_reprocess_state()
    if current_state.get("running"):
        raise HTTPException(
            status_code=409,
            detail=f"Reprocess already running: {current_state['current']}/{current_state['total']} (%{current_state['percentage']})",
        )

    async def event_stream():
        fetcher = FetcherService()
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Story)
                    .where((Story.is_translated.is_(None)) | (Story.is_translated == False))
                    .order_by(Story.created_at.desc())
                )
                stories = result.scalars().all()

                prefs_result = await db.execute(select(UserPreference).limit(1))
                prefs = prefs_result.scalar_one_or_none()
                target_lang_code = prefs.translation_language if prefs else "en"
                target_lang_name = TranslationLanguageResolver.get_language_name(target_lang_code)

                total = len(stories)
                await set_reprocess_state(running=True, current=0, total=total, percentage=0, cancelled=False)
                yield await _sse_event("progress", {"current": 0, "total": total, "percentage": 0, "running": True})

                processed = 0
                errors = 0
                cancelled = False

                for idx, story in enumerate(stories, 1):
                    if await request.is_disconnected():
                        break

                    # Check if user requested cancellation
                    state_check = await get_reprocess_state()
                    if state_check.get("cancelled"):
                        cancelled = True
                        print(f"[SSE/reprocess] Cancelled at {idx}/{total}")
                        yield await _sse_event("cancelled", {"current": idx, "total": total, "percentage": round((idx / total) * 100) if total > 0 else 0})
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

                        pct = round((idx / total) * 100) if total > 0 else 100
                        await set_reprocess_state(current=idx, percentage=pct, story_id=story.id)
                        yield await _sse_event("progress", {"current": idx, "total": total, "percentage": pct, "story_id": story.id, "running": True})
                        yield await _sse_event("story_update", _story_to_dict(story))

                    except Exception as e:
                        errors += 1
                        print(f"[SSE/reprocess] Error reprocessing story {story.id}: {e}")

                if not cancelled:
                    await reset_reprocess_state()
                    yield await _sse_event("complete", {"message": "Done", "total": total, "processed": processed, "errors": errors})

        except Exception as e:
            await reset_reprocess_state()
            yield await _sse_event("error", {"detail": str(e)})
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
    """Reprocess a single story: refetch from HN, re-translate, re-summarize"""
    result = await db.execute(select(Story).where(Story.id == story_id))
    story = result.scalar_one_or_none()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    hn_id = story.hacker_news_id
    if not hn_id:
        raise HTTPException(status_code=400, detail="Story has no HN id")

    fetcher = FetcherService()
    fresh_data = await fetcher.refetch_story_content(int(hn_id), story.url or "")
    if not fresh_data or not fresh_data.get("title"):
        raise HTTPException(status_code=500, detail="Failed to refetch story from HN")

    story.title = fresh_data.get("title", story.title)
    story.url = fresh_data.get("url", story.url)
    story.score = fresh_data.get("score", story.score)
    story.author = fresh_data.get("author", story.author)
    story.content = fresh_data.get("content", story.content)
    await db.commit()

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