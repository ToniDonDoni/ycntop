# Output Artifact Specification

## Primary Files

- `output/top{N}_YYYY-MM-DD.html` (dated HTML report)
- `output/latest.html` (latest run shortcut, overwritten each run)
- `output/top{N}_YYYY-MM-DD.json` (structured export)
- `output/top{N}_YYYY-MM-DD.md` (markdown export)

`N` is the runtime `--top` value (default: `20`).

## HTML Report

Contains:

1. Report title (`YC Top {N}`) and run date.
2. Exact generation timestamp in UTC.
3. Ranked entries with:
   - clickable external article URL,
   - clickable HN discussion URL,
   - final score,
   - metadata-derived summary,
   - 2-3 `why_selected` bullets.
4. LLM status footer:
   - availability/no-key/error state,
   - disabled state for `--no-llm`,
   - limit note when per-run LLM cap is reached.
5. Responsive layout behavior:
   - mobile/desktop mode initialized on load,
   - user toggle button to switch density/layout mode,
   - preference persisted in browser storage.

## Markdown Report

Contains:

1. Report title and date.
2. Per-ranked-story section:
   - title + external URL,
   - HN URL,
   - score,
   - summary,
   - selection reasons.

## JSON Report

Top-level fields:

- `generated_at` (UTC ISO timestamp)
- `items` (ranked story list)

Per-item fields include:

- rank/title/article_url/hn_url
- total score + score components + score details
- summary
- why_selected
- metadata (author, points, comments, story time, word_count, fetch_status)
