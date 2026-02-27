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
            f"<html><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            f"<title>YC Top {requested_top}</title>"
            "<style>:root{--bg:#f5f7fb;--card:#fff;--text:#112233;--muted:#4c6279;--line:#d8e1eb;--link:#0a66cc;}"
            "*{box-sizing:border-box;}body{font-family:Arial,sans-serif;margin:0;background:var(--bg);color:var(--text);line-height:1.55;}"
            ".topbar{position:sticky;top:0;z-index:20;display:flex;justify-content:space-between;align-items:center;gap:.75rem;padding:.7rem 1rem;background:#fff;border-bottom:1px solid var(--line);}"
            ".topbar-title{font-size:.92rem;font-weight:700;color:var(--muted);}#layoutToggle{appearance:none;border:1px solid var(--line);background:#fff;color:var(--text);padding:.4rem .68rem;border-radius:.55rem;font-size:.84rem;cursor:pointer;}"
            ".content{max-width:980px;margin:0 auto;padding:1.25rem;}"
            "article{margin-bottom:1rem;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:.95rem;}"
            "h1{margin:0 0 .5rem;}h2{margin:.1rem 0 .35rem;line-height:1.35;overflow-wrap:anywhere;}"
            "ul{margin-top:.2rem;padding-left:1.1rem;}a{color:var(--link);}footer{max-width:980px;margin:1rem auto;padding:0 1.25rem;color:var(--muted);}"
            "body.compact .content{max-width:640px;}body.compact p,body.compact li{font-size:.97rem;}"
            "@media (max-width:760px){.topbar{padding:.6rem .75rem;}.topbar-title{font-size:.84rem;}"
            ".content{max-width:94vw;padding:.75rem;}article{padding:.8rem;margin-bottom:.75rem;}h1{font-size:1.34rem;}h2{font-size:1.05rem;}p,li{font-size:.98rem;}footer{max-width:94vw;padding:0 .75rem;}}"
            "</style></head><body>"
            "<header class=\"topbar\"><div class=\"topbar-title\">YC Layout</div><button id=\"layoutToggle\" type=\"button\">Compact mode</button></header>"
            "<main class=\"content\">"
            f"<h1>YC Top {requested_top} - {run_date.strftime('%Y-%m-%d')}</h1>"
            f"<p><strong>Generated at:</strong> {generated_utc} (UTC)</p>"
            + "".join(rows)
            + "</main>"
            + f"<footer><strong>{self._llm_status_line(ranked, llm_budget=llm_budget)}</strong></footer>"
            + "<script>(function(){var KEY='yc_layout_mode';var btn=document.getElementById('layoutToggle');if(!btn)return;"
            "function setMode(mode){document.body.classList.toggle('compact',mode==='compact');btn.textContent=mode==='compact'?'Comfortable mode':'Compact mode';}"
            "var saved=localStorage.getItem(KEY);var isMobile=window.matchMedia('(max-width:760px)').matches;var mode=saved||(isMobile?'compact':'comfortable');"
            "setMode(mode);btn.addEventListener('click',function(){var next=document.body.classList.contains('compact')?'comfortable':'compact';setMode(next);localStorage.setItem(KEY,next);});})();</script>"
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
        if all(status == "disabled" for status in statuses):
            return "LLM status: disabled (--no-llm)" + budget_note
        if any(status == "ok" for status in statuses):
            ok_count = sum(1 for s in statuses if s == "ok")
            return f"LLM status: available ({ok_count}/{len(statuses)} titles scored)" + budget_note
        if all(status == "no_api_key" for status in statuses):
            return "LLM status: unavailable (OPENAI_API_KEY not set)" + budget_note
        if any(status in {"error", "parse_error"} for status in statuses):
            return "LLM status: unavailable (OpenAI API call failed)" + budget_note
        return "LLM status: unavailable" + budget_note
