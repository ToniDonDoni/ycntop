# Ranking Strategy

## Objective

Rank recent Hacker News stories using:
- community traction signals from HN metadata,
- recency signals,
- title-level heuristic signal,
- LLM personal-interest signal from titles.

## Inputs Per Story

- `score` (HN points)
- `descendants` (HN comments)
- `time` (story timestamp)
- `title`

## Score Components

- `popularity = score * 0.8 + descendants * 0.2`
- `freshness = max(0, 24 - hours_old)`
- `discussion_heat = min(20, descendants * 0.4)`
- `title_signal` from simple title heuristics (length, punctuation, prefixes)
- `personal_interest` from LLM title scoring (`0..8`)

Total:

`total = popularity + freshness + discussion_heat + title_signal + personal_interest`

## LLM Scoring Behavior

- Titles are sent in batches (default 20 titles per request).
- Prompt requires strict JSON array output with objects:
  - `index`
  - `score`
  - `reason`
- Per-run budget limits how many titles can be scored by LLM (default 500).
- Titles beyond budget are marked `limit_reached` and get neutral personal-interest score.
- If `OPENAI_API_KEY` is missing, all titles get `no_api_key` status and neutral score.

## Sorting and Selection

- Stories are sorted by `total` descending.
- Top `N` (`--top`) are selected for the report.
- `why_selected` contains 2-3 concise reasons derived from score components and thresholds.
