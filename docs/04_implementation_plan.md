# Implementation Plan

## MVP (Phase 1)

Goal: working end-to-end flow without heavy optimization.

1. Parse HN pages and filter by last 24 hours.
2. Open external links and extract text.
3. Rank using heuristic scoring.
4. Generate a top-5 Markdown report.

MVP done criteria:
- one run produces a valid report and survives partial failures.

## Phase 2 (LLM scoring)

1. Integrate OpenAI API article scoring.
2. Enforce structured JSON model output.
3. Combine heuristic and LLM scores into `final_score`.

Done criteria:
- top-5 quality improves and includes clear rationale.

## Phase 3 (hardening)

1. Add caching for downloaded pages.
2. Add retries and backoff for unstable URLs.
3. Add dedup via canonical URL + similar title.
4. Add unit tests for parsing and scoring.

Done criteria:
- reproducible outputs and predictable run time.

## Phase 4 (production)

1. Add scheduler (cron/GitHub Actions), 1-2 runs/day.
2. Publish results to a channel (email/Telegram/Slack).
3. Keep historical reports and trends.

