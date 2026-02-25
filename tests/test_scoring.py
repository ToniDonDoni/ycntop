from datetime import datetime, timezone

from src.models import HNStory
from src.scoring import score_story


def _story(title: str) -> HNStory:
    return HNStory(
        id=1,
        title=title,
        url="https://example.com",
        by="u",
        score=10,
        descendants=2,
        time=datetime(2024, 1, 1, tzinfo=timezone.utc),
        type="story",
    )


def test_personal_interest_boosts_relevant_titles():
    s = score_story(_story("Rust AI benchmark for compiler performance"))
    assert s.components["personal_interest"] > 0


def test_personal_interest_zero_for_generic_title():
    s = score_story(_story("General update about weekly meeting notes"))
    assert s.components["personal_interest"] == 0
