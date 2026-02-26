# Architecture

## End-to-End Flow

1. `src/main.py` parses CLI args (`--hours`, `--top`, `--insecure-llm-ssl`) and orchestrates one run.
2. `src/hn_client.py` fetches `newstories.json`, deduplicates ids, then fetches `item/<id>.json` for each id.
3. Stories are filtered to:
   - `type == story`
   - has `url`
   - `time >= now - hours`
4. The scanner stops early after a streak of consecutive old items (configurable constant) to avoid over-scanning.
5. `src/main.py` builds metadata-only `ArticleContent` records (no external page downloads).
6. `src/ranker.py` requests batched LLM title-interest scores and computes final ranking.
7. `src/report.py` writes HTML/JSON/Markdown outputs and `output/latest.html`.

## Data Sources

- Hacker News ids: `https://hacker-news.firebaseio.com/v0/newstories.json`
- Hacker News item details: `https://hacker-news.firebaseio.com/v0/item/<id>.json`
- OpenAI Responses API for LLM title scoring.

## Core Design Decisions

- Metadata-only pipeline: does not fetch external article bodies.
- LLM scoring is batched to reduce API round-trips (default batch size 20).
- LLM budget is capped per run (default 500 scored titles).
- TLS verification is enabled by default; insecure LLM TLS is opt-in only via CLI flag.
- HTML report escapes untrusted fields before insertion.

## Main Modules

- `src/hn_client.py`: HN API access, filtering, scan progress logging.
- `src/llm_interest.py`: batched title scoring with budget and status handling.
- `src/scoring.py`: deterministic metadata scoring + injected LLM signal.
- `src/ranker.py`: ranking pipeline and selection reasons.
- `src/report.py`: HTML/JSON/MD rendering.
- `src/main.py`: CLI and orchestration.
