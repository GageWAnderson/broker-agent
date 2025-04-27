# ADR 007: Constrained Playwright

## Status
Accepted

## Context
How constrained should we be with web scraping scripts? Fully dynamic LLM generation or a pre-existing script?

## Decision
Start with a pre-existing playwright script for each page. If that script fails, use an evaluator-optimizer agent
to adapt the script to work with the target website.

## Consequences
- Positive: More predictable and reliable web scraping scripts.
- Negative: Less flexible and dynamic - more brittle to changes in the target website.
- Risk: The evaluator-optimizer agent may not work as expected and may make the script worse.

## Date
2025-04-27