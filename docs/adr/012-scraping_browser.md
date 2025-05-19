# ADR 012: Scraping Browser

## Status
Accepted

## Context
IP blocking and throttling is a common technique used by websites to prevent scraping.
Broker agent suffered from both severe IP blocking and throttling.

## Decision
Use a remote browser API to scrape websites.
Use the context configuration managed by the scraping browser to reduce the chance of being blocked or throttled.

## Consequences
- Positive: Very reliable and scraping with minimal IP blocking and throttling.
- Negative: Very costly, both in terms of money, slower connection speed.
- Risk: Reliance on external service, which may fail or be slow.

## Date
2025-05-19