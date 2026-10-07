# Project Execution Plan

## Phase 0 — Requirements and feasibility (complete)
Charter, SRS, functional/non-functional requirements, data/source feasibility, methods, architecture, risk register, test plan and ADRs.

## Phase 1 — Engineering baseline (complete)
Package structure, bootstrap/run scripts, deterministic DEMO mode, connectors, preprocessing, analytics, dashboard, tests and CI.

## Phase 2 — Historical ingestion and coverage-driven scope selection (engineering complete; real acquisition target-machine dependent)
1. Validate CEDA credentials/catalogs.
2. Pilot one commodity/state using resumable historical ingestion.
3. Expand candidate commodity/state coverage in restartable chunks.
4. Run state×commodity quality/coverage audit.
5. Select the final commodity basket from explicit observed coverage criteria plus substantive agricultural relevance.

**Gate:** no final empirical claim before scope review.

## Phase 3 — Spatial and weather enrichment (engineering complete; real enrichment target-machine dependent)
1. Resolve/review stable market coordinates.
2. Cache vector state boundaries with provenance.
3. Acquire NASA POWER weather by source-grid cell × year.
4. Run price dispersion, arrivals-price, lead-lag, influence/integration, distance/QAP, weather-event and market-crunch analyses.

**Gate:** coordinate/weather limitations must remain visible and non-causal interpretation rules apply.

## Phase 4 — Empirical freeze and robustness (engineering complete)
1. Run `readiness-audit` on the explicit commodity/date scope.
2. Resolve any hard failures and review WARN gates.
3. Create a named SHA-256-protected `freeze-scope` snapshot.
4. Verify the snapshot with `verify-freeze`.
5. Run `analyze-freeze` to generate full-period and yearly robustness results.
6. Review edge persistence and year-level leader rankings before describing any market as a persistent price leader.

**Gate:** final-report numbers must come from a verified REAL freeze, never mutable exploratory outputs.

## Phase 5 — Faculty demonstration refinement
- Choose 2–3 strongest REAL commodity case studies supported by the freeze.
- Set dashboard defaults to those case studies without removing nationwide exploration.
- Export SVG figures and concise tables from the frozen findings.
- Prepare interpretation notes for state drill-down, ripple, weather/crunch and geographic-distance views.

## Phase 6 — IEEE-style report
Populate `docs/14_IEEE_REPORT_OUTLINE.md` using only verified frozen-run tables/figures. Report data quality, readiness warnings, sensitivity/temporal-stability evidence, sources and limitations. The dashboard supports the evidence; it is not a substitute for the methodology.
