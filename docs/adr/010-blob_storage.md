# ADR 010: Blob Storage

## Status
Accepted

## Context
We need to store the images for the listings, and we need to store them in a way that is scalable and cost effective.

## Decision
We will use Azure Blob Storage to store the images.

## Consequences
- Positive: Images can be stored in the application for analysis.
- Negative: Increased storage space and complexity of the application.
- Risk: Running out of storage space.

## Date
2025-05-05