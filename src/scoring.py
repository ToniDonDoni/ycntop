from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict

from .llm_interest import score_title_with_llm
from .models import HNStory, ScoreBreakdown


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

    llm_interest = score_title_with_llm(story.title)
    personal_interest = llm_interest.score
    components["personal_interest"] = personal_interest

    total = popularity + freshness + discussion_heat + title_signal + personal_interest
    details = {
        "llm_personal_interest_reason": llm_interest.reason,
        "llm_personal_interest_status": llm_interest.status,
        "llm_model": llm_interest.model,
    }
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
