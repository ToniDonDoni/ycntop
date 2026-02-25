from datetime import datetime, timezone

from src.models import ArticleContent, HNStory
from src.ranker import rank_stories


def _story(idx: int, *, score: int, comments: int) -> HNStory:
    return HNStory(
        id=idx,
        title=f"Story {idx}",
        url=f"https://example.com/{idx}",
        by="user",
        score=score,
        descendants=comments,
        time=datetime(2024, 1, 1, tzinfo=timezone.utc),
        type="story",
    )


def _article(idx: int, *, words: int) -> ArticleContent:
    return ArticleContent(
        url=f"https://example.com/{idx}",
        text="lorem ipsum" * words,
        summary="summary",
        word_count=words,
    )


def test_ranker_selects_top_n():
    stories = [_story(i, score=i * 10, comments=i) for i in range(5)]
    articles = {story.id: _article(story.id, words=1000) for story in stories}
    ranked = rank_stories(stories, articles, top_n=3)
    assert len(ranked) == 3
    assert ranked[0].story.id == 4
    assert ranked[-1].story.id == 2
    for item in ranked:
        assert len(item.why_selected) >= 2


def test_ranker_skips_story_without_article():
    stories = [_story(1, score=150, comments=80), _story(2, score=10, comments=5)]
    articles = {stories[0].id: _article(stories[0].id, words=800)}
    ranked = rank_stories(stories, articles, top_n=5)
    assert len(ranked) == 1
    assert ranked[0].story.id == stories[0].id


def test_ranker_includes_personal_interest_reason():
    story = _story(10, score=200, comments=120)
    story.title = "Rust AI compiler performance benchmark?"
    articles = {story.id: _article(story.id, words=500)}
    ranked = rank_stories([story], articles, top_n=1)
    reasons = ranked[0].why_selected
    assert any("Personal interest" in reason for reason in reasons)
