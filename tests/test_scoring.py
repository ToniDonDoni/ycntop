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


def test_personal_interest_comes_from_llm(monkeypatch):
    class _Fake:
        score = 3.5
        reason = "Looks highly relevant for backend engineers"
        status = "ok"
        model = "fake-model"

    monkeypatch.setattr("src.scoring.score_title_with_llm", lambda title: _Fake())
    s = score_story(_story("Any title"))
    assert s.components["personal_interest"] == 3.5
    assert s.details["llm_personal_interest_status"] == "ok"
    assert s.details["llm_model"] == "fake-model"


def test_personal_interest_zero_when_no_api_key(monkeypatch):
    class _Fake:
        score = 0.0
        reason = "OPENAI_API_KEY not set"
        status = "no_api_key"
        model = "gpt-4.1-mini"

    monkeypatch.setattr("src.scoring.score_title_with_llm", lambda title: _Fake())
    s = score_story(_story("General update about weekly meeting notes"))
    assert s.components["personal_interest"] == 0
    assert s.details["llm_personal_interest_status"] == "no_api_key"
