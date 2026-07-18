"""Backfill script: fetch HN story creation dates for existing stories that have hn_created_at = NULL.

Usage:
    cd /app && python -m app.scripts.backfill_hn_created_at
"""

import asyncio
from datetime import datetime, timezone

from sqlalchemy.future import select

from app.core.database import AsyncSessionLocal
from app.models.story import Story
from app.services.fetcher import FetcherService


async def backfill():
    """Fetch HN creation time for every story that has hn_created_at = NULL."""
    fetcher = FetcherService()
    updated_count = 0
    error_count = 0

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Story).where(Story.hn_created_at.is_(None))
        )
        stories = result.scalars().all()
        total = len(stories)
        print(f"Found {total} stories with missing hn_created_at")

        for i, story in enumerate(stories, 1):
            if not story.hacker_news_id:
                continue
            try:
                hn_id = int(story.hacker_news_id)
                details = await fetcher.fetch_story_details(hn_id)
                hn_time = details.get("time")
                if hn_time:
                    story.hn_created_at = datetime.fromtimestamp(hn_time, tz=timezone.utc)
                    updated_count += 1
                    if updated_count % 10 == 0:
                        await db.commit()
                        print(f"  [{i}/{total}] Committed {updated_count} updates so far...")
                else:
                    error_count += 1
                    print(f"  [{i}/{total}] No 'time' field for HN story {hn_id}")
            except Exception as e:
                error_count += 1
                print(f"  [{i}/{total}] Error fetching HN story {story.hacker_news_id}: {e}")

        await db.commit()
        print(f"\nDone! Updated: {updated_count}, Errors: {error_count}")

    await fetcher.close()


if __name__ == "__main__":
    asyncio.run(backfill())