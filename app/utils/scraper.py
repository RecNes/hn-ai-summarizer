"""Utility functions for web scraping"""

import asyncio
import re

import httpx
from trafilatura import extract


# Browser-like headers to avoid 40X blocks from CDNs/WAFs
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Sec-CH-UA": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "DNT": "1",
    "Connection": "keep-alive",
}


async def scrape_content(url: str) -> str:
    """Scrape main content from URL using browser-like HTTP client + trafilatura parsing.

    Strategy:
      1. Fetch HTML with httpx using full browser headers (bypasses basic bot detection).
      2. Parse with trafilatura.extract() for high-quality article extraction.
      3. If trafilatura yields nothing, fall back to regex-based extraction.
      4. If all fails, return empty string.
    """
    html = await _fetch_with_browser_headers(url)
    if not html:
        return ""

    # Try trafilatura extract() first (pure parser, no network)
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, extract, html)
        if result and len(result.strip()) > 100:
            return result.strip()
    except Exception as exc:
        print(f"trafilatura extract() failed for {url}: {exc}")

    # Fallback: regex extraction
    print(f"trafilatura extracted nothing from {url}, using regex fallback...")
    return _regex_extract(html)


async def _fetch_with_browser_headers(url: str) -> str:
    """Fetch HTML using httpx with full browser emulation headers."""
    async with httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
        headers=_BROWSER_HEADERS,
    ) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.text
        except httpx.HTTPStatusError as e:
            print(
                f"HTTP error {e.response.status_code} for {url}: "
                f"{e.response.reason_phrase}"
            )
        except httpx.TimeoutException as e:
            print(f"Timeout fetching {url}: {e}")
        except httpx.ConnectError as e:
            print(f"Connection error fetching {url}: {e}")
        except Exception as e:
            print(f"Unexpected error fetching {url}: {e}")
    return ""


def _regex_extract(html: str) -> str:
    """Extract readable text from HTML using regex patterns.

    Pure-fallback when trafilatura cannot parse the content.
    """
    # 1. Remove script and style tags
    html = re.sub(
        r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE
    )
    html = re.sub(
        r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE
    )

    # 2. Extract <p> and <li> text
    paragraphs = re.findall(
        r'<p[^>]*>(.*?)</p>', html, re.DOTALL | re.IGNORECASE
    )
    list_items = re.findall(
        r'<li[^>]*>(.*?)</li>', html, re.DOTALL | re.IGNORECASE
    )

    # 3. Also try <article> blocks
    articles = re.findall(
        r'<article[^>]*>(.*?)</article>', html, re.DOTALL | re.IGNORECASE
    )

    def strip_tags(text: str) -> str:
        return re.sub(r'<[^>]+>', '', text).strip()

    content_parts: list[str] = []
    if articles:
        for art in articles:
            content_parts.append(strip_tags(art))
    content_parts.extend(strip_tags(p) for p in paragraphs)
    content_parts.extend(strip_tags(li) for li in list_items)

    # 4. Filter out empty/short lines
    lines = [part for part in content_parts if len(part.strip()) > 30]

    if lines:
        result = "\n".join(lines)
        if len(result) > 200:
            return result[:5000]

    # 5. Last resort: get all visible text from body
    body_match = re.search(
        r'<body[^>]*>(.*?)</body>', html, re.DOTALL | re.IGNORECASE
    )
    if body_match:
        text = strip_tags(body_match.group(1))
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) > 200:
            return text[:5000]

    return ""