# Design / Build Iteration Log

## Iteration 0 — Concept decomposition
Separated the project into market data, weather, geography, network inference and presentation. Rejected pure price forecasting as the main objective.

## Iteration 1 — Research-method refinement
Replaced the phrase “market controls produce prices” with “statistical market price leadership/influence.” Rejected price-level cross-correlation because common trends/seasonality can create spurious relationships; adopted aligned log returns plus significance/FDR checks.

## Iteration 2 — Data-source feasibility
Verified the Government of India OGD AGMARKNET daily resource, CEDA historical AGMARKNET API surface, IMD rainfall pages/API documentation, NASA POWER daily API and government/NIC GeoJSON-capable state boundaries. Added an adapter/import architecture because API authentication and availability can change.

## Iteration 3 — Reproducibility and failure design
Added explicit REAL vs DEMO data modes, deterministic fixture generation, persistent provenance, caches, graceful connector failures and CSV import paths. Decided that fallback data must never be silently mixed into empirical output.

## Iteration 4 — Software engineering freeze
Finalized functional/non-functional requirements, schemas, analytics, architecture, UX, test plan, risk register and traceability matrix **before implementation**. Implementation proceeds only against these frozen documents; later deviations must be recorded as ADRs.

## Iteration 5 — Historical API hardening
Replaced the legacy CEDA placeholder contract with the current `/v1/agmarknet` endpoint structure, Bearer authentication, ID/name catalog resolution, market-level price/quantity merging and explicit response-envelope validation.

## Iteration 6 — Resumability and empirical scope gate
Added commodity×district×calendar-year checkpoints, dry-run job planning, cached catalog snapshots, failed-job ledger, deterministic panel rebuild and a formal coverage-driven commodity selection table. This completes the Phase 2 engineering gate before any final-paper empirical claims are frozen.


## Iteration — Phase 3 spatial/weather hardening (2026-10-05)
1. Identified name-only market identity as unsafe for national joins; introduced stable state+district+market IDs.
2. Audited graph semantics and corrected sink-oriented PageRank to source-oriented PageRank for leader ranking.
3. Replaced one-shot weather fetching with resumable POWER cell × year checkpoints at approximately source-grid resolution.
4. Added reviewed coordinate-import path and restricted public Nominatim to explicit, policy-compliant small batches.
5. Added state-boundary provenance and open geoBoundaries fallback because BharatMaps service access can be institutionally restricted.
6. Replaced naïve spatial pair significance as the primary statistic with a QAP-style market-label permutation diagnostic.
7. Declustered weather extremes and changed event responses to use real pre-event/response observation dates.
8. Reframed ripple visualization to show follower daily returns at inferred edge lags, matching the network statistic.
9. Added regression tests and reran full demo analysis before release packaging.

## Iteration — Phase 4 empirical freeze and robustness hardening (2026-10-06)
1. Separated mutable exploratory analysis from paper-grade evidence using named empirical snapshots.
2. Added explicit REAL-only, provenance, coverage, coordinate and weather readiness gates before final freezes.
3. Added per-file SHA-256 integrity manifests and a verification command so post-hoc data changes are detectable.
4. Added independent calendar-year network re-estimation to quantify edge persistence instead of relying only on pooled-period leadership.
5. Added year-level leader-rank stability tables to prevent one anomalous subperiod from defining a market as a persistent leader.
6. Added a freeze-local analysis runner and machine-generated non-causal results summary.
7. Added dashboard Research Status view so the demonstrator visibly distinguishes exploratory state from frozen evidence.
8. Added known-answer tamper-detection and two-year persistent-lag tests before release packaging.

## Iteration — Phase 5 provenance and real-data bootstrap hardening (2026-10-07)
1. Identified that REAL/DEMO alone cannot distinguish official evidence from a genuine but secondary mirror.
2. Introduced authority tiers for primary official, curated official-derived, secondary mirror, user-supplied and demo data.
3. Added a final-paper hard gate that rejects non-authoritative source tiers even when the observations are REAL.
4. Prevented generic CSV imports from self-promoting to official tiers; official OGD and CEDA exports now use dedicated import paths.
5. Added schema-tolerant CEDA/OGD manual-export mapping to preserve continuity when credentials or upstream APIs are temporarily unavailable.
6. Added per-import SHA-256 provenance records and an offline `doctor` command.
7. Added Phase 5 known-answer tests and reran the full regression suite before packaging.
