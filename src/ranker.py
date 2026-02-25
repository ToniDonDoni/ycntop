from __future__ import annotations

from typing import Dict, Iterable, List

from .models import ArticleContent, HNStory, RankedStory, ScoreBreakdown
from .scoring import score_story


def rank_stories(stories: Iterable[HNStory], articles: Dict[int, ArticleContent], *, top_n: int) -> List[RankedStory]:
    enriched = []
    for story in stories:
        article = articles.get(story.id)
        if not article:
            continue
        score = score_story(story)
        enriched.append((score.total, story, article, score))
    enriched.sort(key=lambda row: row[0], reverse=True)
    ranked: List[RankedStory] = []
    for idx, (_, story, article, score) in enumerate(enriched[:top_n], start=1):
        why_selected = _default_reasons(story, score)
        ranked.append(RankedStory(rank=idx, story=story, article=article, score=score, why_selected=why_selected))
    return ranked


def _default_reasons(story: HNStory, score: ScoreBreakdown) -> list[str]:
    reasons = []
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
    if personal_interest >= 3 and len(reasons) < 3:
        reasons.append("Editorially interesting headline signal")
    if "?" in story.title and len(reasons) < 3:
        reasons.append("Question-style headline drives curiosity")
    pi = score.components.get("personal_interest", 0)
    matches = score.details.get("personal_interest_keywords", []) if hasattr(score, "details") else []
    pi_reason = None
    if pi >= 2.0:
        if matches:
            rendered = ", ".join(matches[:2])
            pi_reason = f"Personal interest boost (keywords: {rendered})"
        else:
            pi_reason = "Personal interest boost from editorial heuristics"
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
