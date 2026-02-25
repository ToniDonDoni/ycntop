from datetime import datetime, timezone
from pathlib import Path

from src.models import ArticleContent, HNStory, RankedStory, ScoreBreakdown
from src.report import ReportBuilder


def _ranked(idx: int) -> RankedStory:
    story = HNStory(
        id=idx,
        title=f"Story {idx}",
        url=f"https://example.com/{idx}",
        by="user",
        score=100,
        descendants=40,
        time=datetime(2024, 1, 1, tzinfo=timezone.utc),
        type="story",
    )
    article = ArticleContent(
        url=story.url,
        text="lorem" * 50,
        summary="summary",
        word_count=500,
    )
    breakdown = ScoreBreakdown(total=150.0, components={"popularity": 100, "freshness": 48, "depth": 2})
    return RankedStory(rank=idx, story=story, article=article, score=breakdown, why_selected=["reason a", "reason b"])


def test_report_builder_creates_files(tmp_path: Path):
    builder = ReportBuilder(output_dir=tmp_path)
    ranked = [_ranked(i) for i in range(1, 3)]
    run_date = datetime(2024, 1, 2, tzinfo=timezone.utc)
    builder.render(ranked, run_date=run_date)
    slug = run_date.strftime("%Y-%m-%d")
    html = tmp_path / f"top5_{slug}.html"
    latest = tmp_path / "latest.html"
    assert html.exists()
    assert (tmp_path / f"top5_{slug}.json").exists()
    assert (tmp_path / f"top5_{slug}.md").exists()
    assert latest.exists()
    content = html.read_text()
    assert "YYC Top 5" in content
    assert "Why selected" in content
    latest_content = latest.read_text()
    assert "HN Thread" in latest_content
