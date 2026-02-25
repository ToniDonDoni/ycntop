# Output Artifact Specification

## Primary Files

- `output/top5_YYYY-MM-DD.html` (primary user-facing report)
- `output/latest.html` (latest run shortcut, overwritten each run)
- `output/top5_YYYY-MM-DD.json` (structured data export)
- `output/top5_YYYY-MM-DD.md` (text export)

## HTML Report (Primary)

Contains:
1. Run date and time.
2. Summary counts: found, processed, excluded.
3. Top-5 entries with:
   - rank,
   - clickable title to original article,
   - clickable `HN discussion` URL,
   - final score,
   - short summary,
   - `why_selected` (2-3 bullets).

## Markdown Report

Contains:
1. Run date and time.
2. Summary: found, processed, excluded counts.
3. Top-5 entries, each with:
   - rank,
   - title,
   - external URL,
   - HN URL,
   - final score,
   - short summary,
   - `why_selected` (2-3 bullets).

## JSON Schema (simplified)

```json
{
  "run_at": "2026-02-23T22:00:00Z",
  "window_hours": 24,
  "totals": {
    "candidates": 120,
    "fetched": 98,
    "parsed": 90,
    "ranked": 78,
    "selected": 5
  },
  "top": [
    {
      "rank": 1,
      "hn_id": 123,
      "title": "...",
      "external_url": "https://...",
      "hn_url": "https://news.ycombinator.com/item?id=123",
      "scores": {
        "base": 0.78,
        "llm": 0.82,
        "final": 0.80
      },
      "summary": "...",
      "why_selected": ["...", "..."]
    }
  ]
}
```

## Optional Artifacts

- `output/logs/run_YYYY-MM-DD_HHMM.log`
- `output/cache/*.html`
