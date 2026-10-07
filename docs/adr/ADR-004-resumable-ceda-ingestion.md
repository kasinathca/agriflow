# ADR-004 — Resumable CEDA historical ingestion

**Status:** Accepted

## Context
The final study requires multi-year market-level historical data. National pulls can span many districts and may be interrupted by network failures or API throttling.

## Decision
Use one checkpoint per commodity × state × district × calendar-year interval. Successful and empty jobs are explicitly recorded; failures are written to an error ledger. Rebuild the processed panel only from completed local chunks.

## Consequences
- long runs can resume safely;
- provenance is inspectable at a small unit of work;
- storage overhead is higher than a single monolithic file;
- catalog/API changes can be isolated by run date.
