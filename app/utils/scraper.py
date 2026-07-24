"""Utility for scraping web content from article URLs."""

import logging
import re

import httpx
import trafilatura

logger = logging.getLogger(__name__)


def _regex_extract(html: str) -> str:
    """Fallback extraction using simple regex patterns."""
    # Remove script and style tags
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)

    # Extract text from common content tags
    patterns = [
        r'<article[^>]*>(.*?)</article>',
        r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>',
        r'<div[^>]*class="[^"]*post[^"]*"[^>]*>(.*?)</div>',
        r'<p>(.*?)</p>',
    ]

    texts = []
    for pattern in patterns:
        matches = re.findall(pattern, html, re.DOTALL)
        for match in matches:
            # Strip HTML tags
            clean = re.sub(r'<[^>]+>', '', match).strip()
            if len(clean) > 50:  # Only include substantial paragraphs
                texts.append(clean)

    return '\n'.join(texts)


async def scrape_content(url: str) -> str:
    """Scrape article content from URL using trafilatura with regex fallback."""
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            try:
                response = await client.get(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                })
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                logger.error(
                    "HTTP error %s for %s: %s",
                    e.response.status_code, url, e.response.text[:200],
                )
                return ""
            except httpx.TimeoutException as e:
                logger.error("Timeout fetching %s: %s", url, e)
                return ""
            except httpx.ConnectError as e:
                logger.error("Connection error fetching %s: %s", url, e)
                return ""
            except Exception as e:
                logger.error("Unexpected error fetching %s: %s", url, e)
                return ""

            html = response.text

            # Try trafilatura extraction
            try:
                text = trafilatura.extract(html, output_format='txt', include_links=False)
                if text:
                    return text.strip()[:5000]
            except Exception as exc:
                logger.warning(
                    "trafilatura extract() failed for %s: %s", url, exc,
                )

            # Fallback: regex extraction
            logger.info(
                "trafilatura extracted nothing from %s, using regex fallback...", url,
            )
            return _regex_extract(html)
    except Exception as e:
        logger.error("Unexpected error fetching %s: %s", url, e)
    return ""