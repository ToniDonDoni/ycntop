from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List

from .models import HNStory, ScoreBreakdown

INTEREST_KEYWORDS = {
    "rust": 3.0,
    "python": 2.2,
    "ai": 2.8,
    "llm": 2.6,
    "open source": 2.4,
    "linux": 2.0,
    "compiler": 2.0,
    "database": 1.8,
    "security": 2.0,
    "privacy": 1.8,
    "benchmark": 1.6,
    "performance": 1.6,
    "show hn": 2.0,
    "ask hn": 1.4,
}


def score_story(story: HNStory) -> ScoreBreakdown:
    """Heuristic scoring that relies entirely on Hacker News metadata."""

    components: Dict[str, float] = {}

    popularity = story.score * 0.8 + story.descendants * 0.2
    components["popularity"] = popularity

    hours_old = _hours_old(story)
    freshness = max(0.0, 24 - hours_old)
    components["freshness"] = freshness

    discussion_heat = min(20.0, story.descendants * 0.4)
    components["discussion_heat"] = discussion_heat

    title_signal = _title_signal(story.title)
    components["title_signal"] = title_signal

    personal_interest, interest_matches = _personal_interest(story.title)
    components["personal_interest"] = personal_interest

    total = popularity + freshness + discussion_heat + title_signal + personal_interest
    details = {"personal_interest_keywords": interest_matches}
    return ScoreBreakdown(total=total, components=components, details=details)


def _title_signal(title: str) -> float:
    tokens = title.split()
    long_words = sum(1 for token in tokens if len(token) >= 6)
    bonus = 1.5 if ":" in title else 0.0
    if "?" in title:
        bonus += 1.5
    if title.lower().startswith(("ask hn", "show hn")):
        bonus += 1.0
    score = long_words * 0.5 + bonus
    return min(10.0, score)


def _hours_old(story: HNStory) -> float:
    return (datetime.now(timezone.utc) - story.time).total_seconds() / 3600


def _personal_interest(title: str) -> tuple[float, List[str]]:
    """A simple editorial taste signal based on title keywords."""

    lowered = title.lower()
    score = 0.0
    matches: List[str] = []
    for phrase, weight in INTEREST_KEYWORDS.items():
        if phrase in lowered:
            score += weight
            matches.append(phrase)
    if any(token.isdigit() for token in lowered.split()):
        score += 0.5
    return min(8.0, score), matches
