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
    breakdown = ScoreBreakdown(
        total=150.0,
        components={"popularity": 100, "freshness": 48, "depth": 2},
        details={"llm_personal_interest_status": "no_api_key"},
    )
    return RankedStory(rank=idx, story=story, article=article, score=breakdown, why_selected=["reason a", "reason b"])


def test_report_builder_creates_files(tmp_path: Path):
    builder = ReportBuilder(output_dir=tmp_path)
    ranked = [_ranked(i) for i in range(1, 3)]
    run_date = datetime(2024, 1, 2, tzinfo=timezone.utc)
    requested_top = 10
    builder.render(ranked, run_date=run_date, requested_top=requested_top)
    slug = run_date.strftime("%Y-%m-%d")
    html = tmp_path / f"top{requested_top}_{slug}.html"
    latest = tmp_path / "latest.html"
    favicon = tmp_path / "favicon.svg"
    assert html.exists()
    assert (tmp_path / f"top{requested_top}_{slug}.json").exists()
    assert (tmp_path / f"top{requested_top}_{slug}.md").exists()
    assert latest.exists()
    assert favicon.exists()
    content = html.read_text()
    assert "YC Top 10" in content
    assert 'rel="icon"' in content
    assert 'href="favicon.svg"' in content
    assert "Generated at:" in content
    assert "2024-01-02 00:00:00 UTC (UTC)" in content
    assert "@media (max-width:760px)" in content
    assert "id=\"layoutToggle\"" in content
    assert "matchMedia('(max-width:760px)')" in content
    assert "localStorage.getItem(KEY)" in content
    assert "Why selected" in content
    latest_content = latest.read_text()
    assert "HN Thread" in latest_content
    assert "LLM status: unavailable (OPENAI_API_KEY not set)" in latest_content
    assert "<svg" in favicon.read_text()


def test_report_builder_shows_llm_available_status(tmp_path: Path):
    builder = ReportBuilder(output_dir=tmp_path)
    ranked_item = _ranked(1)
    ranked_item.score.details["llm_personal_interest_status"] = "ok"
    run_date = datetime(2024, 1, 2, tzinfo=timezone.utc)
    builder.render([ranked_item], run_date=run_date, requested_top=3)
    html = (tmp_path / f"top3_{run_date.strftime('%Y-%m-%d')}.html").read_text()
    assert "LLM status: available (1/1 titles scored)" in html


def test_report_builder_shows_llm_disabled_status(tmp_path: Path):
    builder = ReportBuilder(output_dir=tmp_path)
    ranked_item = _ranked(1)
    ranked_item.score.details["llm_personal_interest_status"] = "disabled"
    run_date = datetime(2024, 1, 2, tzinfo=timezone.utc)
    builder.render([ranked_item], run_date=run_date, requested_top=3)
    html = (tmp_path / f"top3_{run_date.strftime('%Y-%m-%d')}.html").read_text()
    assert "LLM status: disabled (--no-llm)" in html


def test_report_builder_shows_llm_limit_note(tmp_path: Path):
    builder = ReportBuilder(output_dir=tmp_path)
    ranked_item = _ranked(1)
    ranked_item.score.details["llm_personal_interest_status"] = "ok"
    run_date = datetime(2024, 1, 2, tzinfo=timezone.utc)
    builder.render(
        [ranked_item],
        run_date=run_date,
        requested_top=10,
        llm_budget={"max_calls": 500, "calls_used": 500, "limit_reached": 1},
    )
    html = (tmp_path / f"top10_{run_date.strftime('%Y-%m-%d')}.html").read_text()
    assert "LLM call limit reached (500/500)" in html


def test_report_builder_escapes_untrusted_html_fields(tmp_path: Path):
    builder = ReportBuilder(output_dir=tmp_path)
    ranked_item = _ranked(1)
    ranked_item.story.title = '<img src=x onerror=alert("xss-title")>'
    ranked_item.story.url = 'https://example.com/news?q="><script>alert(1)</script>'
    ranked_item.article.summary = '<script>alert("xss-summary")</script>'
    ranked_item.why_selected = ['<b onclick="alert(2)">reason</b>']
    run_date = datetime(2024, 1, 2, tzinfo=timezone.utc)
    builder.render([ranked_item], run_date=run_date, requested_top=5)
    html = (tmp_path / f"top5_{run_date.strftime('%Y-%m-%d')}.html").read_text()

    assert "<script>alert" not in html
    assert "&lt;img src=x onerror=alert(&quot;xss-title&quot;)&gt;" in html
    assert "&lt;script&gt;alert(&quot;xss-summary&quot;)&lt;/script&gt;" in html
    assert "&lt;b onclick=&quot;alert(2)&quot;&gt;reason&lt;/b&gt;" in html
    assert "https://example.com/news?q=&quot;&gt;&lt;script&gt;alert(1)&lt;/script&gt;" in html
