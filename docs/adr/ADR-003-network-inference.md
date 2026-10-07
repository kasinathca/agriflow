# ADR-003 — Lead-lag inference on returns with FDR control

**Status:** Accepted

## Decision
Infer directed candidate transmission edges from log-price returns rather than raw price levels; require minimum overlap, effect-size threshold and Benjamini-Hochberg adjusted significance.

## Rationale
Raw price levels share trend and seasonality and can create misleading correlations. Return-based analysis is more conservative and the multiple-testing correction is necessary when comparing many market pairs.
