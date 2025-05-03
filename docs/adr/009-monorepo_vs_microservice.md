# ADR 009: Monorepo vs Microservice

## Status
Accepted

## Context
Choosing how to structure the project. Should we use a monorepo or a microservice architecture?
Microservices are more flexible and easier to scale, but they are also more complex to manage.

## Decision
Use a monorepo for now since this is a personal project not for production use.

## Consequences
- Positive: Simpler to manage and deploy.
- Negative: Reduced flexibility and scalability.
- Risk: Increased risk of data inconsistency.

## Date
2025-05-03