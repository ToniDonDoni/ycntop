import json
from datetime import datetime, timezone

from src.main import run_pipeline
from src.models import HNStory
from src.report import ReportBuilder


class _StubHNClient:
    def __init__(self, stories):
        self._stories = stories

    def fetch_recent_stories(self, *, hours, max_items):
        return self._stories


def _story(idx: int) -> HNStory:
    return HNStory(
        id=idx,
        title=f"Story {idx}?",
        url=f"https://example.com/{idx}",
        by="tester",
        score=100 + idx,
        descendants=50 + idx,
        time=datetime(2024, 1, 1, tzinfo=timezone.utc),
        type="story",
    )


def test_run_pipeline_does_not_fetch_articles(monkeypatch, tmp_path):
    called = {"fetch": False}

    def fake_fetch(*args, **kwargs):
        called["fetch"] = True
        raise AssertionError("fetch_url should not be called")

    monkeypatch.setattr("src.article_fetcher.fetch_url", fake_fetch)

    stories = [_story(1), _story(2)]
    client = _StubHNClient(stories)
    builder = ReportBuilder(output_dir=tmp_path)
    run_time = datetime(2024, 1, 2, tzinfo=timezone.utc)

    ranked = run_pipeline(24, 2, client=client, report_builder=builder, now=run_time)

    assert len(ranked) == 2
    assert called["fetch"] is False

    slug = run_time.strftime("%Y-%m-%d")
    json_path = tmp_path / f"top2_{slug}.json"
    payload = json.loads(json_path.read_text())
    assert payload["items"][0]["why_selected"]
    assert all("points" in item["summary"] for item in payload["items"])
    assert "score_details" in payload["items"][0]
