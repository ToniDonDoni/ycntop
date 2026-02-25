from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from .models import RankedStory


class ReportBuilder:
    def __init__(self, *, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def render(self, ranked: List[RankedStory], *, run_date: datetime) -> None:
        date_slug = run_date.strftime("%Y-%m-%d")
        html_path = self.output_dir / f"top5_{date_slug}.html"
        json_path = self.output_dir / f"top5_{date_slug}.json"
        md_path = self.output_dir / f"top5_{date_slug}.md"
        latest = self.output_dir / "latest.html"

        html_content = self._render_html(ranked, run_date)
        md_content = self._render_md(ranked, run_date)

        html_path.write_text(html_content, encoding="utf-8")
        json_path.write_text(self._render_json(ranked), encoding="utf-8")
        md_path.write_text(md_content, encoding="utf-8")
        latest.write_text(html_content, encoding="utf-8")

    def _render_html(self, ranked: List[RankedStory], run_date: datetime) -> str:
        rows = []
        for item in ranked:
            article_link = f"<a href=\"{item.story.url}\" target=\"_blank\">{item.story.title}</a>"
            hn_link = f"<a href=\"https://news.ycombinator.com/item?id={item.story.id}\" target=\"_blank\">HN Thread</a>"
            bullets = "".join(f"<li>{bullet}</li>" for bullet in item.why_selected)
            rows.append(
                f"<article>"
                f"<h2>{item.rank}. {article_link}</h2>"
                f"<p>Score: {item.score.total:.2f} | {hn_link}</p>"
                f"<p>{item.article.summary}</p>"
                f"<p><strong>Why selected:</strong></p><ul>{bullets}</ul>"
                f"</article>"
            )
        html = (
            "<html><head><meta charset=\"utf-8\"><title>YYC Top 5</title>"
            "<style>body{font-family:Arial;margin:2rem;}article{margin-bottom:1.5rem;}"
            "h2{margin-bottom:0.2rem;}ul{margin-top:0.2rem;}"
            "</style></head><body>"
            f"<h1>YYC Top 5 - {run_date.strftime('%Y-%m-%d')}</h1>"
            + "".join(rows)
            + "</body></html>"
        )
        return html

    def _render_md(self, ranked: List[RankedStory], run_date: datetime) -> str:
        lines = [f"# YYC Top 5 - {run_date.strftime('%Y-%m-%d')}"]
        for item in ranked:
            lines.append(
                f"## {item.rank}. [{item.story.title}]({item.story.url})"
                f" ( [HN](https://news.ycombinator.com/item?id={item.story.id}) )"
            )
            lines.append(f"**Score:** {item.score.total:.2f}")
            lines.append(item.article.summary)
            for reason in item.why_selected:
                lines.append(f"- {reason}")
            lines.append("")
        return "\n".join(lines)

    def _render_json(self, ranked: List[RankedStory]) -> str:
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "items": [item.to_export_dict() for item in ranked],
        }
        return json.dumps(payload, indent=2)
