# ADR 001: Simple Architecture

## Status
Accepted

## Context
We need a simple architecture that is easy to understand and easy to maintain.
Therefore, we will use python to handle both the agentic logic and the actual web scraping.
Introducing an additional Next/NodeJS tool not worth the added complexity for the extra brower
functionality given that this project will just be scraping a small number of websites.

## Decision
Use python + LangChain + Playwright to handle the agentic logic and the actual web scraping.

## Consequences
- Positive: Simple and easy to understand.
- Negative: Misses out on scalable browser automation like [Browserbase](https://www.browserbase.com/).
- Risk: Python based web scraping tooling misses several key features for web scraping like navigating IP bans,
stealth, CAPTCHA solving, etc.

## Date
04-26-2025