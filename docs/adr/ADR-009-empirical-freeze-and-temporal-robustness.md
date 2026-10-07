# ADR-009 — Checksum-Protected Empirical Freeze and Temporal Robustness

## Status
Accepted for v1.3.0.

## Context
Exploratory dashboards are mutable: filters, source refreshes, corrected coordinates and newly downloaded weather can change results. A final academic paper requires the exact analytical input to be reconstructable. In addition, a network inferred over several years can conceal time instability.

## Decision
1. Final-report analysis SHALL operate on a named frozen snapshot rather than directly on mutable `data/processed/` files.
2. Frozen input files SHALL be accompanied by SHA-256 hashes and a machine-readable manifest.
3. DEMO data SHALL block an empirical freeze unless an explicit testing-only override is supplied.
4. Lead-lag networks SHALL be re-estimated by evaluable calendar year for temporal-stability diagnostics.
5. A pooled full-period leader SHALL NOT automatically be described as persistent; year-level rankings and edge persistence SHALL be available for review.

## Consequences
- Reproducibility and academic auditability improve substantially.
- Correcting source data requires a new freeze rather than silently overwriting the old evidence base.
- Some commodities/markets may have too little within-year overlap for stability estimates; this absence is reported rather than imputed.
