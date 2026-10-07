# ADR-010 — Separate REAL/DEMO mode from source-authority tier

**Status:** Accepted  
**Date:** 2026-10-07

## Context
A dataset can contain genuine observed mandi prices while still being unsuitable as final academic evidence if it came from a secondary mirror, an unverified local file or a source whose provenance cannot be reconstructed. A binary REAL/DEMO flag cannot represent that distinction.

## Decision
AgriFlow SHALL retain `data_mode` for synthetic-versus-observed status and SHALL add `source_tier` for provenance authority. Final empirical freezes SHALL accept only `PRIMARY_OFFICIAL` and `CURATED_OFFICIAL_DERIVED` rows. Generic import commands SHALL NOT allow a user to self-label a file as official; dedicated OGD/CEDA import routes assign those tiers.

## Consequences
- Secondary mirrors remain useful for bootstrap/debugging without becoming citable evidence by accident.
- Manual official exports remain usable when an API credential/interface is unavailable, provided the raw export and context are retained.
- Older REAL imports without source-tier metadata may fail the paper gate and need to be rebuilt/re-imported through a dedicated source path.
