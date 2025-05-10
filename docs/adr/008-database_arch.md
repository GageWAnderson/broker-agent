# ADR 000: Database Architecture

## Status
Accepted

## Context
Should the relational database store the metadata about apartment listings?
Or should everything be handled inside a vector DB?

## Decision
Use both a vector DB and a relational DB. Allows the best of both worlds both for metadata filtering
and SQL statements over apartments in the relational database.

## Consequences
- Positive: Allows both the rich embedding and metadata filtering of the vector DB and the SQL statements
of the relational DB.
- Negative: Increased complexity and effort to keep the two databases in sync.
- Risk: Increased risk of data inconsistency.

## Date
2025-05-03