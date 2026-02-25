# YC News Curator (YC)

A project for automatically selecting the 5 best Hacker News stories from the last 24 hours.

## Goal

On each run, the system should:
- collect fresh stories from Hacker News;
- analyze titles + HN metadata (points, comments, age) without fetching article pages;
- score candidates using clear heuristics;
- produce a top-5 list with short explanations grounded in metadata;
- save results as an HTML page with clickable links (plus JSON/Markdown exports).

## Main Output (HTML)

Primary output files after each run:
- `output/top20_YYYY-MM-DD.html` — dated report (when using defaults)
- `output/latest.html` — always points to the most recent run

The HTML page includes:
- top-5 ranked stories;
- clickable story title linking to the original article;
- clickable `HN discussion` link;
- score, short summary, and selection reasons.

## Documentation Included

- Concept: `docs/01_concept.md`
- Architecture and modules: `docs/02_architecture.md`
- Scoring and ranking strategy: `docs/03_ranking_strategy.md`
- Implementation plan (MVP -> v1): `docs/04_implementation_plan.md`
- Risks and limitations: `docs/05_risks_and_limits.md`
- Tech stack and dependencies: `docs/06_tech_stack.md`
- Output artifact specification: `docs/07_output_spec.md`

## Setup

1. Ensure Python 3.11+ is available locally.
2. (Recommended) Create a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   ```
3. Install development dependencies:
   ```bash
   pip install -r requirements.txt  # if you add optional deps later
   pip install pytest               # needed for bundled tests
   ```
   `certifi` is included in `requirements.txt` and is used for verified TLS to HN/OpenAI APIs.

## Running YC

Execute the pipeline from the repo root:

```bash
python -m src.main run --hours 12 --top 20
```

Key flags:
- `--hours` limits candidates to the most recent N hours (default 12).
- `--top` controls how many ranked results to emit (default 20).
- `--insecure-llm-ssl` disables TLS certificate verification only for OpenAI LLM requests in the current run (debug/emergency use only).

Scoring blends Hacker News metadata (points, comments, freshness, title structure) with an LLM-based `personal_interest` signal inferred from each title. If `OPENAI_API_KEY` is present, the script calls OpenAI to score title-level interest and stores the LLM reason in score details. If no key is set, `personal_interest` is neutral (0) and ranking continues normally. The command never downloads article pages; summaries and rationales are derived purely from title/metadata so the run succeeds even if every external host blocks bots.

## Generated Artifacts

Every successful run writes the following into `output/`:

- `top20_YYYY-MM-DD.html` – dated HTML report with clickable article and HN links, score, summary, and “why selected” bullets (when using defaults).
- `top20_YYYY-MM-DD.json` – structured data with the score breakdown, metadata, and per-item fields (when using defaults).
- `top20_YYYY-MM-DD.md` – Markdown summary for quick sharing (when using defaults).
- `latest.html` – copy of the newest HTML run for easy bookmarking.

## Testing

Run the bundled tests to validate recency filtering, ranking logic, pipeline behavior, and report generation:

```bash
pytest
```

## GitHub Actions

- `Tests` workflow runs `pytest -q` on every push and pull request.
- `Manual Latest Report` workflow is manual (`Run workflow` button in GitHub Actions), runs on the branch selected in the UI, generates the report, and uploads artifacts including:
  - `output/latest.html`
  - dated `output/top*.html`, `output/top*.json`, `output/top*.md`
- `Deploy Latest Report to Pages` workflow is manual and publishes `output/latest.html` to GitHub Pages as `index.html`.

If you want LLM scoring in GitHub Actions, add repository secret `OPENAI_API_KEY`.

## Troubleshooting

- **Empty results** – typically caused by temporary HN API/network failures. Re-run later or extend `--hours`.
- **No HTML/JSON emitted** – make sure `output/` exists and that the process has write permissions.
- **HTML/JSON mismatch** – re-run `pytest` to ensure serializer/report tests cover your adjustments.
- **Stale rankings** – ensure the machine clock is correct; freshness heuristics rely on UTC timestamps from HN.
