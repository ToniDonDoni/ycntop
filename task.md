# Task: Build YC MVP with Executor + Reviewer Loop

## Workspace
current workspace (repository root)

## Objective
Implement an MVP of **YC News Curator (YC)** that collects Hacker News stories from the last 24 hours, ranks them by title-level signals only, and outputs top-5 results.

## Scope (MVP)

1. Fetch Hacker News candidates from the last 24 hours.
2. Do not open external links and do not download article pages.
3. Compute ranking scores from title + HN metadata and select top 5.
4. Generate outputs:
   - `output/top5_YYYY-MM-DD.html` (primary)
   - `output/latest.html` (latest run)
   - `output/top5_YYYY-MM-DD.json`
   - `output/top5_YYYY-MM-DD.md`

## HTML Output Requirements (strict)
For each top item include:
- rank
- clickable article title (original URL)
- clickable HN discussion link
- final score
- short summary generated from title/HN metadata only (no page scraping)
- `why_selected` with 2-3 bullet points based on title/HN metadata only
- if `personal_interest` materially contributed, mention that in `why_selected`

## Technical Requirements
- Python 3.11+
- Modular code in `src/`
- Recommended modules:
  - `src/main.py`
  - `src/hn_client.py`
  - `src/article_fetcher.py`
  - `src/article_parser.py`
  - `src/scoring.py`
  - `src/ranker.py`
  - `src/report.py`
- CLI entrypoint:
  - `python -m src.main run --hours 24 --top 5`
- Do not call external article URLs at all (no `fetch_url` for article pages in runtime pipeline).
- Ranking must work even if every article host blocks bots, because no article host should be queried.

## Ranking (MVP-friendly)
- Use practical heuristic scoring from:
  - title quality/relevance heuristics,
  - HN points,
  - HN comments,
  - freshness.
- Add a deterministic subjective component `personal_interest` that reflects whether the title looks interesting editorially.
  - Keep it explainable (keyword/heuristic-based).
  - Include it in score breakdown exports.
- If LLM scoring is implemented, keep fallback mode when no API key is present.
- Record score fields in JSON output.

## Tests and Validation
Add at least minimal tests for:
- HN item parsing/filtering by age
- ranker top-N behavior
- report generation shape
- pipeline behavior that confirms external article URLs are not fetched
- scoring behavior that validates `personal_interest` contributes for relevant titles

Provide a short validation note:
- what was run,
- what passed,
- what remains untested.

## Documentation Updates
Update `README.md` with:
- install/setup steps,
- run command,
- output files,
- quick troubleshooting notes.

## Non-Goals
- No UI framework/web server required.
- No production scheduler required in MVP.

## Review Instructions (for reviewer agent)
Review for:
1. Correctness of 24h filtering and top-5 selection.
2. HTML links are valid and present for each selected item.
3. External article pages are not fetched at all.
4. Output schema consistency across HTML/JSON/MD.
5. Test coverage for core logic and regression risk.

Severity labels expected in review findings:
- P0 critical breakage
- P1 major functional issue
- P2 moderate issue
- P3 minor improvement

## Done Criteria
Task is done when:
- CLI runs end-to-end,
- required output files are generated,
- HTML includes clickable links and top-5 details,
- tests pass (or failures are explicitly explained),
- reviewer signs off or provides actionable findings.
