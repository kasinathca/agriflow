# ADR-008 — Spatial boundaries, coordinates and weather acquisition

## Status
Accepted.

## Decision
- Use reviewed market-coordinate imports as the preferred national coordinate source.
- Restrict public Nominatim to explicit small one-time batches under its usage policy.
- Cache vector ADM1 boundaries with provenance; use NIC/BharatMaps when accessible and geoBoundaries gbOpen as the reproducible open fallback.
- Acquire NASA POWER weather by deduplicated source-grid cell × year checkpoints.

## Rationale
This balances reproducibility, licensing, public-service usage limits and national-scale reliability.

## Consequences
Coordinate quality and boundary provider are part of provenance. POWER values are described as gridded weather estimates, not local station measurements.
