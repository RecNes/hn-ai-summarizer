"""Utility functions for keyword extraction and matching"""

import re
from typing import Set


def extract_keywords(text: str) -> Set[str]:
    """Extract keywords from text"""
    if not text:
        return set()

    # Simple keyword extraction - in a real implementation, you might use NLP
    # Remove punctuation and split into words
    words = re.findall(r"\b\w+\b", text.lower())

    # Filter out common stop words and short words
    stop_words = {
        "the",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "must",
        "can",
        "this",
        "that",
        "these",
        "those",
        "i",
        "you",
        "he",
        "she",
        "it",
        "we",
        "they",
        "me",
        "him",
        "her",
        "us",
        "them",
    }

    keywords = {word for word in words if len(word) > 2 and word not in stop_words}
    return keywords


def match_keywords(text: str, keywords_list: str) -> bool:
    """Check if text matches any of the keywords"""
    if not text or not keywords_list:
        return False

    text_keywords = extract_keywords(text)
    target_keywords = {
        kw.strip().lower() for kw in keywords_list.split(",") if kw.strip()
    }

    # Check for any matching keywords
    return bool(text_keywords.intersection(target_keywords))


def highlight_text(text: str, keywords_list: str) -> str:
    """Highlight keywords in text"""
    if not text or not keywords_list:
        return text

    target_keywords = {
        kw.strip().lower() for kw in keywords_list.split(",") if kw.strip()
    }

    # Simple highlighting - in a real implementation, you might want more sophisticated highlighting
    highlighted_text = text
    for keyword in target_keywords:
        # Case insensitive replacement with highlighting
        highlighted_text = re.sub(
            f"({re.escape(keyword)})",
            r"<mark>\1</mark>",
            highlighted_text,
            flags=re.IGNORECASE,
        )

    return highlighted_text
