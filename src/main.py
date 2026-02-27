from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from .hn_client import HNClient
from .llm_interest import (
    DEFAULT_MAX_CALLS,
    get_llm_budget_state,
    reset_llm_budget,
    set_llm_enabled,
    set_llm_expected_calls,
    set_llm_insecure_ssl,
)
from .models import ArticleContent, HNStory, RankedStory
from .ranker import rank_stories
from .report import ReportBuilder

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
LOGGER = logging.getLogger(__name__)


def run_pipeline(
    hours: int,
    top_n: int,
    *,
    no_llm: bool = False,
    insecure_llm_ssl: bool = False,
    client: Optional[HNClient] = None,
    report_builder: Optional[ReportBuilder] = None,
    now: Optional[datetime] = None,
) -> List[RankedStory]:
    set_llm_enabled(not no_llm)
    set_llm_insecure_ssl(insecure_llm_ssl)
    reset_llm_budget(DEFAULT_MAX_CALLS)
    client = client or HNClient()
    run_time = now or datetime.now(timezone.utc)
    stories = client.fetch_recent_stories(hours=hours)
    LOGGER.info("Fetched %s candidate stories", len(stories))
    set_llm_expected_calls(len(stories))

    articles: Dict[int, ArticleContent] = {}
    for story in stories:
        articles[story.id] = _article_from_metadata(story, run_time)

    ranked = rank_stories(stories, articles, top_n=top_n)
    LOGGER.info("Ranked %s stories", len(ranked))

    report = report_builder or ReportBuilder(output_dir=Path("output"))
    report.render(ranked, run_date=run_time, requested_top=top_n, llm_budget=get_llm_budget_state())
    return ranked


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="YC News Curator (YC)")
    sub = parser.add_subparsers(dest="command", required=True)
    run_cmd = sub.add_parser("run", help="Execute the YC pipeline")
    run_cmd.add_argument("--hours", type=int, default=12)
    run_cmd.add_argument("--top", type=int, default=20)
    run_cmd.add_argument(
        "--insecure-llm-ssl",
        action="store_true",
        help="Disable TLS certificate verification only for OpenAI LLM requests in this run.",
    )
    run_cmd.add_argument(
        "--no-llm",
        action="store_true",
        help="Disable all LLM scoring calls (use metadata-only ranking for fast layout/testing runs).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        run_pipeline(hours=args.hours, top_n=args.top, no_llm=args.no_llm, insecure_llm_ssl=args.insecure_llm_ssl)
        return 0
    parser.print_help()
    return 1


def _article_from_metadata(story: HNStory, run_time: datetime) -> ArticleContent:
    hours_old = max(0.0, (run_time - story.time).total_seconds() / 3600)
    if hours_old < 1:
        age_text = "under an hour ago"
    else:
        age_text = f"{hours_old:.1f}h ago"
    summary = (
        f"{story.title} — shared by {story.by} about {age_text}. "
        f"Currently at {story.score} points with {story.descendants} comments on Hacker News."
    )
    word_count = len(summary.split())
    return ArticleContent(
        url=story.url,
        text=story.title,
        summary=summary,
        word_count=word_count,
        fetch_status="metadata_only",
    )


if __name__ == "__main__":
    raise SystemExit(main())
