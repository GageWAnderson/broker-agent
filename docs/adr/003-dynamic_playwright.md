# ADR 003: Dynamic Playwright

## Status
Accepted

## Context
How constrained should we be with web scraping scripts? Fully dynamic LLM generation or a pre-existing script?
Balance between constrained and dynamic - generate a script based on previous scripts that are in the database.

## Decision
Use a pre-existing script and generate a new one based on previous scripts that are in the database.

## Consequences
- Positive: Allows dynamic adaptiveness to the target website while not being so open-ended it causes failures.
- Negative: Removes some flexibility from the tool.
- Risk: The tool isn't a generalist tool - it's targeted at a specific websites (also old scripts may not work with new websites).

## Date
04/26/2025