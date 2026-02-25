# Ranking Strategy

## What "best article" means

A top-5 article should be:
- substantive,
- practically useful,
- relevant to a tech/product/startup audience,
- not clickbait,
- ideally supported by HN community signals.

## Two-Stage Scoring

## Stage A: fast heuristics (low cost)

Compute a baseline `base_score`:
- `text_quality_score` (0-1): length + extraction quality.
- `hn_signal_score` (0-1): normalized `points` and `comments`.
- `freshness_score` (0-1): newer items score higher.

Example:

`base_score = 0.45 * text_quality_score + 0.35 * hn_signal_score + 0.20 * freshness_score`

Then optionally remove low-quality candidates (for example, bottom 30-40%).

## Stage B: LLM scoring (higher cost)

For remaining candidates, the model evaluates:
- `insight_score` (depth and usefulness of ideas),
- `novelty_score` (how new/original),
- `applicability_score` (practical actionability),
- `credibility_score` (quality of evidence/argumentation).

Final score:

`final_score = 0.40 * base_score + 0.60 * llm_score`

where:

`llm_score = 0.30 * insight + 0.25 * novelty + 0.30 * applicability + 0.15 * credibility`

## Exclusion Rules

Exclude stories if:
- article text cannot be extracted;
- extracted text is too short (for example, < 400 chars);
- hard paywall/no readable content;
- duplicate URL or near-duplicate content.

## Explainability

For each top-5 item, store:
- numeric scores;
- 2-3 reasons for selection;
- a short summary.

