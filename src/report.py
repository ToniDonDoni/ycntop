from __future__ import annotations

import json
from html import escape
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from .models import RankedStory


class ReportBuilder:
    def __init__(self, *, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def render(
        self,
        ranked: List[RankedStory],
        *,
        run_date: datetime,
        requested_top: int = 5,
        llm_budget: Optional[Dict[str, int]] = None,
    ) -> None:
        date_slug = run_date.strftime("%Y-%m-%d")
        html_path = self.output_dir / f"top{requested_top}_{date_slug}.html"
        json_path = self.output_dir / f"top{requested_top}_{date_slug}.json"
        md_path = self.output_dir / f"top{requested_top}_{date_slug}.md"
        latest = self.output_dir / "latest.html"

        html_content = self._render_html(ranked, run_date, requested_top, llm_budget=llm_budget)
        md_content = self._render_md(ranked, run_date, requested_top)

        html_path.write_text(html_content, encoding="utf-8")
        json_path.write_text(self._render_json(ranked), encoding="utf-8")
        md_path.write_text(md_content, encoding="utf-8")
        latest.write_text(html_content, encoding="utf-8")

    def _render_html(
        self,
        ranked: List[RankedStory],
        run_date: datetime,
        requested_top: int,
        *,
        llm_budget: Optional[Dict[str, int]] = None,
    ) -> str:
        generated_utc = run_date.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        rows = []
        for item in ranked:
            safe_url = escape(item.story.url, quote=True)
            safe_title = escape(item.story.title)
            safe_summary = escape(item.article.summary)
            article_link = f"<a href=\"{safe_url}\" target=\"_blank\" rel=\"noopener noreferrer\">{safe_title}</a>"
            hn_link = f"<a href=\"https://news.ycombinator.com/item?id={item.story.id}\" target=\"_blank\">HN Thread</a>"
            bullets = "".join(f"<li>{escape(bullet)}</li>" for bullet in item.why_selected)
            rows.append(
                f"<article>"
                f"<h2>{item.rank}. {article_link}</h2>"
                f"<p>Score: {item.score.total:.2f} | {hn_link}</p>"
                f"<p>{safe_summary}</p>"
                f"<p><strong>Why selected:</strong></p><ul>{bullets}</ul>"
                f"</article>"
            )
        html = (
            f"<html><head><meta charset=\"utf-8\"><title>YC Top {requested_top}</title>"
            "<style>body{font-family:Arial;margin:2rem;}article{margin-bottom:1.5rem;}"
            "h2{margin-bottom:0.2rem;}ul{margin-top:0.2rem;}footer{margin-top:2rem;color:#555;}"
            "</style></head><body>"
            f"<h1>YC Top {requested_top} - {run_date.strftime('%Y-%m-%d')}</h1>"
            f"<p><strong>Generated at:</strong> {generated_utc} (UTC)</p>"
            + "".join(rows)
            + f"<footer><strong>{self._llm_status_line(ranked, llm_budget=llm_budget)}</strong></footer>"
            + "</body></html>"
        )
        return html

    def _render_md(self, ranked: List[RankedStory], run_date: datetime, requested_top: int) -> str:
        lines = [f"# YC Top {requested_top} - {run_date.strftime('%Y-%m-%d')}"]
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

    def _llm_status_line(self, ranked: List[RankedStory], *, llm_budget: Optional[Dict[str, int]] = None) -> str:
        budget_note = ""
        if llm_budget and int(llm_budget.get("limit_reached", 0)) == 1:
            used = int(llm_budget.get("calls_used", 0))
            limit = int(llm_budget.get("max_calls", 0))
            budget_note = f" | LLM call limit reached ({used}/{limit}); remaining titles scored without LLM."

        statuses = []
        for item in ranked:
            status = item.score.details.get("llm_personal_interest_status")
            if isinstance(status, str) and status:
                statuses.append(status)

        if not statuses:
            return "LLM status: unavailable (no LLM scoring metadata)" + budget_note
        if any(status == "ok" for status in statuses):
            ok_count = sum(1 for s in statuses if s == "ok")
            return f"LLM status: available ({ok_count}/{len(statuses)} titles scored)" + budget_note
        if all(status == "no_api_key" for status in statuses):
            return "LLM status: unavailable (OPENAI_API_KEY not set)" + budget_note
        if any(status in {"error", "parse_error"} for status in statuses):
            return "LLM status: unavailable (OpenAI API call failed)" + budget_note
        return "LLM status: unavailable" + budget_note
