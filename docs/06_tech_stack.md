# Tech Stack

## Language and Environment

- Python 3.11+
- `venv` for isolation

## Libraries

- `httpx` — HTTP client
- `beautifulsoup4` + `lxml` — HTML parsing
- `trafilatura` — main text extraction
- `pydantic` — typed data models
- `tenacity` — retries/backoff
- `rich` (optional) — improved CLI output
- `openai` — LLM-based scoring

## Testing and Quality

- `pytest`
- `ruff`
- `mypy` (optional early on)

## Why this stack

- Fast MVP setup without infrastructure overhead.
- Reliable, common tooling for scraping + extraction.
- Easy path to scale from script to service.

