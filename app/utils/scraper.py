"""Utility functions for web scraping"""

import asyncio
import re

import httpx
from trafilatura import extract, fetch_url


async def scrape_content(url: str) -> str:
    """Scrape main content from URL using trafilatura, with fallback."""
    try:
        loop = asyncio.get_event_loop()
        downloaded = await loop.run_in_executor(None, fetch_url, url)
        if downloaded:
            result = await loop.run_in_executor(None, extract, downloaded)
            if result and len(result.strip()) > 100:
                return result.strip()

        # Fallback: try httpx directly (handles some JS-heavy sites better)
        print(f"trafilatura returned empty for {url}, trying httpx fallback...")
        return await _fallback_scrape(url)

    except Exception as e:
        print(f"Error scraping {url} via trafilatura: {e}")
        try:
            return await _fallback_scrape(url)
        except Exception as e2:
            print(f"Fallback scrape also failed for {url}: {e2}")
            return ""


async def _fallback_scrape(url: str) -> str:
    """Fallback scraper using httpx to fetch raw HTML and extract text."""
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        try:
            response = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })
            response.raise_for_status()
            html = response.text
        except Exception as e:
            print(f"Fallback HTTP request failed for {url}: {e}")
            return ""

    # Extract text content from HTML
    # 1. Remove script and style tags
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    
    # 2. Extract <p> and <li> text (best for articles)
    paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL | re.IGNORECASE)
    list_items = re.findall(r'<li[^>]*>(.*?)</li>', html, re.DOTALL | re.IGNORECASE)
    
    # 3. Also try <article> and main content divs
    articles = re.findall(r'<article[^>]*>(.*?)</article>', html, re.DOTALL | re.IGNORECASE)
    
    # 4. Strip HTML tags from extracted pieces
    def strip_tags(text):
        return re.sub(r'<[^>]+>', '', text).strip()
    
    content_parts = []
    if articles:
        for art in articles:
            content_parts.append(strip_tags(art))
    content_parts.extend(strip_tags(p) for p in paragraphs)
    content_parts.extend(strip_tags(li) for li in list_items)
    
    # 5. Filter out empty/short lines and join
    lines = []
    for part in content_parts:
        part = part.strip()
        if len(part) > 30:  # Skip very short fragments
            lines.append(part)
    
    result = "\n".join(lines)
    
    if len(result) > 200:
        return result[:5000]  # Limit to 5000 chars
    
    # 6. Last resort: get visible text from body
    body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL | re.IGNORECASE)
    if body_match:
        text = strip_tags(body_match.group(1))
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) > 200:
            return text[:5000]
    
    return ""