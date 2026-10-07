# ADR-006 — Pan-India market identity

## Status
Accepted.

## Decision
Use a stable normalized identifier derived from `state + district + market` for every market-level analytical join and graph node. Retain the source display name separately.

## Rationale
Mandi names are not guaranteed globally unique. Name-only joins can merge unrelated markets and corrupt national network, spatial and weather results without obvious runtime errors.

## Consequences
Legacy fixtures without geography may fall back to a display-name identifier only for unit-test compatibility; real ingestion must carry state and district.
