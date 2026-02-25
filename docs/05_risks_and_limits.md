# Risks and Limitations

## Technical

- Some links fail (403, paywall, JS-only rendering).
- Article extraction may return noisy or partial text.
- Some HN items point to discussion pages instead of source content.

## Quality

- "Best" is partly subjective.
- High HN points do not always mean high content quality.
- LLMs may overrate well-written but weakly substantiated content.

## Operational

- Runtime and cost increase with candidate volume.
- API limits and third-party outages can affect runs.

## Mitigations

- Two-stage filtering (heuristics -> LLM).
- Structured logs with skip reasons.
- `MAX_ARTICLES` limits and batching.
- Retries and fallback mode without LLM.

