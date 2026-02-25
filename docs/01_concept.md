# Concept

## Problem

The Hacker News feed moves quickly. Many links appear each day, and manually reading and comparing all of them is time-consuming.

## Idea

Build an autonomous curator script that:
1. fetches stories from the last 24 hours;
2. opens each external link;
3. extracts the main article text;
4. scores content quality and usefulness;
5. returns the best 5 stories with a short rationale.

## Principles

- Transparency: every top-5 pick includes an explicit reason.
- Reproducibility: same inputs should produce similar outputs.
- Resilience: failed links should not break the full run.
- Cost control: use cheap heuristics first, then LLM scoring.

## Non-Functional Requirements

- Full run target: up to 10-15 minutes (depends on volume).
- Partial fault tolerance: process at least 80% of links under normal network conditions.
- Logging: record why stories were skipped.

