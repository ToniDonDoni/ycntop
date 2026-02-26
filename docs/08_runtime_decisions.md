# Runtime Decisions (Current)

This document captures the current implementation decisions used in production runs.

## Defaults

- Default lookback window: `12` hours.
- Default output size: top `20`.

## Data Collection

- Candidate ids are pulled from HN `newstories`.
- Candidate details are loaded via `item/<id>.json`.
- Duplicate ids are removed before item fetch.
- Recency filter uses `item.time` compared against `now - hours`.

## Scan Stop Policy

- Scan proceeds in recency-first order over `newstories`.
- Scan stops early after a configured streak of consecutive old stories.
- Rationale: avoid scanning the full id list once the stream has clearly crossed the cutoff.

## LLM Integration

- LLM scoring uses OpenAI Responses API.
- Titles are scored in batches (default `20` titles/request).
- Per-run scored-title cap: `500`.
- If the cap is reached, remaining titles are not sent to LLM.
- If key is missing/API fails, ranking continues with neutral LLM contribution.

## Security and Reliability

- TLS verification is on by default.
- Insecure TLS for LLM is explicit opt-in via CLI flag only.
- HTML report escapes all untrusted fields before rendering.

## Reporting

- Outputs: HTML, JSON, Markdown.
- `output/latest.html` always points to the most recent run.
- HTML report includes exact generation timestamp in UTC.
