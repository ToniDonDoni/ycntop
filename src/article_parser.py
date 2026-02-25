from __future__ import annotations

import logging
import re

LOGGER = logging.getLogger(__name__)

EXTRACTION_FALLBACK_MIN_WORDS = 50


def clean_html(raw_html: str) -> str:
    """Remove script/style tags and collapse whitespace for readability."""

    cleaned = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", raw_html)
    cleaned = re.sub(r"(?s)<[^>]+>", " ", cleaned)
    cleaned = re.sub(r"&nbsp;", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def summarize_text(text: str, *, max_sentences: int = 3) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    summary = " ".join(sentences[:max_sentences]).strip()
    if not summary:
        summary = text[:240].strip()
    return summary


def parse_article(raw_html: str, *, url: str) -> tuple[str, str, int]:
    text = clean_html(raw_html)
    word_count = len(text.split())
    if word_count < EXTRACTION_FALLBACK_MIN_WORDS:
        LOGGER.debug("Article at %s seems short (words=%s)", url, word_count)
    summary = summarize_text(text)
    return text, summary, word_count
