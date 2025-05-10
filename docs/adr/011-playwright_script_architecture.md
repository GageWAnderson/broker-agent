# ADR 011 Playwright Script Architecture

## Status
Accepted

## Context
Maintaining a database of playwright scripts is a challenge and creates a lot of code and storage overhead
for not much benefit.

## Decision
Use hardcoded playwright scripts for now for scraping a targeted number of websites.
Get to MVP with hardcoded scripts and then use LLM to generate playwright scripts for new websites.

## Consequences
- Positive: More reliable scripts in the short term.
- Negative: Brittle scripts if the DOM changes for any target sites.
- Risk: N/A

## Date
2025-05-10