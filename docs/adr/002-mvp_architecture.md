# ADR 002: MVP Architecture

## Status
Accepted

## Context
Use the [Evaluator-optimizer](https://www.anthropic.com/engineering/building-effective-agents) workflow to the MVP.
Use [parallelization](https://www.anthropic.com/engineering/building-effective-agents) workflow for the MVP.

## Decision
Go with a simpler architecture for the MVP - don't over-complicate the parallelism.

## Consequences
- Positive: Faster to implement with less opportunities for race conditions.
- Negative: Scraping/search of different websites will need to be done serially (slower).
- Risk: Searching of sites is slower.

## Date
04/26/2025