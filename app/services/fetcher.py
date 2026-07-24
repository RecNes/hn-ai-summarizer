"""Service to fetch and process Hacker News stories and comments."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.utils.scraper import scrape_content

logger = logging.getLogger(__name__)


class FetcherService:
    """Service to fetch and process Hacker News stories and comments."""

    HN_API_BASE = "https://hacker-news.firebaseio.com/v0"

    def __init__(self):
        self._client: httpx.AsyncClient | None = None
        # Track failed story IDs for later retry
        self._failed_stories: List[Dict[str, Any]] = []

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient()
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    @property
    def failed_stories(self) -> List[Dict[str, Any]]:
        """Return the list of stories that failed during this fetch cycle."""
        return self._failed_stories

    async def _throttle(self):
        """Wait between HN API requests to avoid rate limiting."""
        delay = settings.HN_REQUEST_DELAY
        if delay > 0:
            await asyncio.sleep(delay)

    async def fetch_top_stories(self, limit: int = 100) -> List[int]:
        """Fetch top story IDs from Hacker News"""
        client = await self._get_client()
        try:
            response = await client.get(f"{self.HN_API_BASE}/topstories.json")
            response.raise_for_status()
            story_ids = response.json()
            return story_ids[:limit]
        except Exception as e:
            logger.error("Error fetching top stories: %s", e)
            return []

    async def fetch_story_details(self, story_id: int) -> Dict[str, Any]:
        """Fetch details for a specific story with throttle."""
        await self._throttle()
        client = await self._get_client()
        try:
            response = await client.get(f"{self.HN_API_BASE}/item/{story_id}.json")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                "Error fetching story %s: HTTP %s - %s",
                story_id, e.response.status_code, e.response.text[:200],
            )
            return {}
        except httpx.TimeoutException as e:
            logger.error("Error fetching story %s: TIMEOUT - %s", story_id, e)
            return {}
        except Exception as e:
            logger.error(
                "Error fetching story %s: %s: %s", story_id, type(e).__name__, e,
            )
            return {}

    async def fetch_comments(
        self, story_id: int, kid_ids: Optional[List[int]] = None, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Fetch top comments for a story.

        If kid_ids are provided (from the story data), use them directly
        to avoid an extra API call to fetch the story again.
        """
        try:
            # Use provided kid_ids if available, otherwise fetch story to get them
            comment_ids = kid_ids[:limit] if kid_ids else None
            if comment_ids is None:
                story = await self.fetch_story_details(story_id)
                if "kids" in story:
                    comment_ids = story["kids"][:limit]

            if not comment_ids:
                return []

            comments = []
            for cid in comment_ids:
                try:
                    comment = await self.fetch_story_details(cid)
                    if comment and "text" in comment and comment.get("text", "").strip():
                        comments.append(comment)
                except Exception as e:
                    logger.error("Error fetching comment %s: %s", cid, e)
            return comments
        except Exception as e:
            logger.error(
                "Error fetching comments for story %s: %s", story_id, e,
            )
            return []

    async def process_story(self, story_id: int) -> Dict[str, Any]:
        """Process a story: fetch details, scrape content, and get comments"""
        story = await self.fetch_story_details(story_id)
        if not story or story.get("type") != "story":
            return {}

        # Scrape content if URL exists
        content = ""
        if story.get("url"):
            try:
                content = await scrape_content(story["url"])
            except Exception as e:
                logger.error("Error scraping content for %s: %s", story.get("url"), e)

        # Fetch comments using already-fetched kid IDs (no extra API call)
        kid_ids = story.get("kids")
        comments = await self.fetch_comments(story_id, kid_ids=kid_ids)

        hn_time = story.get("time")
        hn_created_at = (
            datetime.fromtimestamp(hn_time, tz=timezone.utc)
            if hn_time
            else None
        )

        return {
            "hacker_news_id": str(story_id),
            "title": story.get("title", ""),
            "url": story.get("url", ""),
            "score": story.get("score", 0),
            "author": story.get("by", ""),
            "content": content,
            "comments": comments,
            "hn_created_at": hn_created_at,
        }

    async def fetch_and_process_stories(
        self, min_score: int = 100, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Fetch and process top stories above minimum score"""
        story_ids = await self.fetch_top_stories(limit)
        stories = []
        self._failed_stories = []

        # Process stories sequentially to respect throttle delay
        for story_id in story_ids:
            try:
                result = await self.process_story(story_id)
                if result and result.get("score", 0) >= min_score:
                    stories.append(result)
            except Exception as e:
                logger.error("Error processing story %s: %s", story_id, e)
                # Collect failed stories for later retry
                self._failed_stories.append({
                    "hacker_news_id": str(story_id),
                    "url": "",
                    "title": f"[failed {story_id}]",
                })

        if self._failed_stories:
            logger.warning(
                "%s stories failed during fetch, will be retried after delay.",
                len(self._failed_stories),
            )

        return stories

    async def refetch_story_content(
        self, story_id: int, story_url: str = ""
    ) -> Dict[str, Any]:
        """Refetch content for an existing story"""
        story = await self.fetch_story_details(story_id)
        if not story:
            return {}

        # Scrape content if URL exists
        content = ""
        url = story_url or story.get("url")
        if url:
            try:
                content = await scrape_content(url)
            except Exception as e:
                logger.error("Error scraping content for %s: %s", url, e)

        # Fetch comments using kid_ids
        kid_ids = story.get("kids")
        comments = await self.fetch_comments(story_id, kid_ids=kid_ids)

        hn_time = story.get("time")
        hn_created_at = (
            datetime.fromtimestamp(hn_time, tz=timezone.utc)
            if hn_time
            else None
        )

        return {
            "hacker_news_id": str(story_id),
            "title": story.get("title", ""),
            "url": url,
            "score": story.get("score", 0),
            "author": story.get("by", ""),
            "content": content,
            "comments": comments,
            "hn_created_at": hn_created_at,
        }