from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class HNStory:
    """Representation of a Hacker News story we may process."""

    id: int
    title: str
    url: str
    by: str
    score: int
    descendants: int
    time: datetime
    type: str = "story"
    text: Optional[str] = None


@dataclass
class ArticleContent:
    """Synthesised article details derived from metadata (no external fetch)."""

    url: str
    text: str = ""
    summary: str = ""
    word_count: int = 0
    fetch_status: str = "metadata_only"


@dataclass
class ScoreBreakdown:
    total: float
    components: Dict[str, float] = field(default_factory=dict)
    details: Dict[str, object] = field(default_factory=dict)


@dataclass
class RankedStory:
    rank: int
    story: HNStory
    article: ArticleContent
    score: ScoreBreakdown
    why_selected: List[str] = field(default_factory=list)

    def to_export_dict(self) -> Dict[str, object]:
        return {
            "rank": self.rank,
            "title": self.story.title,
            "article_url": self.story.url,
            "hn_url": f"https://news.ycombinator.com/item?id={self.story.id}",
            "score": self.score.total,
            "score_components": self.score.components,
            "score_details": self.score.details,
            "summary": self.article.summary,
            "why_selected": self.why_selected,
            "metadata": {
                "author": self.story.by,
                "points": self.story.score,
                "comments": self.story.descendants,
                "fetched_at": self.story.time.isoformat(),
                "word_count": self.article.word_count,
                "fetch_status": self.article.fetch_status,
            },
        }
