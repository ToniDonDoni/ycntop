from __future__ import annotations

import os
from typing import Dict, Iterable, List

from .llm_interest import DEFAULT_BATCH_SIZE, score_titles_with_llm_batch
from .models import ArticleContent, HNStory, RankedStory, ScoreBreakdown
from .scoring import score_story

PERSONAL_INTEREST_REASON_THRESHOLD = 4.0


def rank_stories(stories: Iterable[HNStory], articles: Dict[int, ArticleContent], *, top_n: int) -> List[RankedStory]:
    batch_size = _llm_batch_size()
    candidates = [story for story in stories if articles.get(story.id)]
    llm_results = score_titles_with_llm_batch([story.title for story in candidates], batch_size=batch_size)
    enriched = []
    for story, llm_result in zip(candidates, llm_results):
        article = articles[story.id]
        score = score_story(story, llm_interest=llm_result)
        enriched.append((score.total, story, article, score))
    enriched.sort(key=lambda row: row[0], reverse=True)
    ranked: List[RankedStory] = []
    for idx, (_, story, article, score) in enumerate(enriched[:top_n], start=1):
        why_selected = _default_reasons(story, score)
        ranked.append(RankedStory(rank=idx, story=story, article=article, score=score, why_selected=why_selected))
    return ranked


def _default_reasons(story: HNStory, score: ScoreBreakdown) -> list[str]:
    reasons: List[str] = []
    if story.score >= 150:
        reasons.append("Exceptional community interest (>=150 points)")
    elif story.score >= 75:
        reasons.append("High community interest (>=75 points)")
    if story.descendants >= 60:
        reasons.append("Very active discussion (>=60 comments)")
    elif story.descendants >= 30:
        reasons.append("Active discussion (>=30 comments)")
    freshness = score.components.get("freshness", 0)
    if freshness >= 18:
        reasons.append("Fresh submission (<=6h old)")
    elif freshness <= 4:
        reasons.append("Still trending after a full day")
    personal_interest = score.components.get("personal_interest", 0)
    if personal_interest >= PERSONAL_INTEREST_REASON_THRESHOLD and len(reasons) < 3:
        reasons.append("Editorially interesting headline signal")
    if "?" in story.title and len(reasons) < 3:
        reasons.append("Question-style headline drives curiosity")
    pi = score.components.get("personal_interest", 0)
    llm_reason = score.details.get("llm_personal_interest_reason", "") if hasattr(score, "details") else ""
    llm_status = score.details.get("llm_personal_interest_status", "") if hasattr(score, "details") else ""
    pi_reason = None
    if pi >= PERSONAL_INTEREST_REASON_THRESHOLD:
        if llm_reason:
            status_suffix = f", status={llm_status}" if llm_status and llm_status != "ok" else ""
            pi_reason = f"LLM interest score (+{pi:.2f}{status_suffix}): {llm_reason}"
        else:
            status_suffix = f", status={llm_status}" if llm_status and llm_status != "ok" else ""
            pi_reason = f"LLM interest score (+{pi:.2f}{status_suffix})"
        reasons.append(pi_reason)
    while len(reasons) < 2:
        reasons.append("Strong metadata-driven score vs peers")
    if len(reasons) > 3:
        if pi_reason and pi_reason in reasons:
            base = [r for r in reasons if r != pi_reason][:2]
            reasons = base + [pi_reason]
        else:
            reasons = reasons[:3]
    return reasons


def _llm_batch_size() -> int:
    raw = os.getenv("YYC_LLM_BATCH_SIZE", str(DEFAULT_BATCH_SIZE)).strip()
    try:
        value = int(raw)
    except Exception:
        return DEFAULT_BATCH_SIZE
    return max(1, min(value, 50))
