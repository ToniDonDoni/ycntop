# Architecture

## Data Flow

1. **HN Fetcher**
   - Pulls stories from the last 24 hours.
   - Source: HN HTML pages (`news`, `newest`) or API.

2. **Candidate Builder**
   - Normalizes fields:
     - `hn_id`, `title`, `hn_url`, `external_url`, `age_hours`, `points`, `comments`.

3. **Content Fetcher**
   - Downloads each external URL (timeouts, retries, user-agent).

4. **Content Extractor**
   - Extracts readable article text (removes nav/ads/noise).

5. **Scoring Engine**
   - Stage A (heuristics): text quality, length, HN signals.
   - Stage B (LLM): content quality, practical value, novelty.

6. **Ranker**
   - Combines scores and selects top-5.

7. **Reporter**
   - Writes `output/top5_YYYY-MM-DD.md` and `output/top5_YYYY-MM-DD.json`.

## Suggested Modules

- `src/hn_client.py` — fetch HN stories.
- `src/article_fetcher.py` — fetch external pages.
- `src/article_parser.py` — extract article text.
- `src/scoring.py` — heuristics + LLM scoring.
- `src/ranker.py` — final top-N selection.
- `src/report.py` — report generation.
- `src/main.py` — CLI and orchestration.

## Configuration

`.env` / environment variables:
- `OPENAI_API_KEY`
- `MODEL_NAME` (e.g., `gpt-5-mini`)
- `REQUEST_TIMEOUT_SEC`
- `MAX_ARTICLES`
- `TOP_N`

