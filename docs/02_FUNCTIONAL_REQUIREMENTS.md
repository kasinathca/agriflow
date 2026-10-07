# Functional Requirements

| ID | Requirement | Acceptance criterion |
|---|---|---|
| FR-01 | Bootstrap environment | Windows/Linux bootstrap creates venv, installs pinned dependencies and initializes config/data. |
| FR-02 | Demo startup | With no API keys, app launches using an explicitly labelled deterministic demo fixture. |
| FR-03 | Real AGMARKNET ingestion | Connector fetches daily records from data.gov.in when `DATA_GOV_API_KEY` is supplied. |
| FR-04 | Historical ingestion path | CEDA connector/import pathway supports historical price/arrival data with a CEDA key or exported files. |
| FR-05 | Weather ingestion | NASA POWER connector downloads/caches rainfall and temperature by spatial grid cell/date range. |
| FR-06 | IMD reference | IMD state rainfall connector can retrieve current/reference rainfall fields when reachable. |
| FR-07 | Geographic data | Official/NIC state GeoJSON is downloaded/cached; fallback presentation is clearly indicated if unavailable. |
| FR-08 | Validation | Schema, dates, numeric ranges, duplicates and min≤modal≤max consistency are checked. |
| FR-09 | Coverage audit | State×commodity reporting completeness and observation counts are computed. |
| FR-10 | Price dispersion | Cross-market dispersion metrics are computed by date/commodity. |
| FR-11 | Supply-price analysis | Arrival-price correlations and log-log elasticity estimates are produced with sample-size guards. |
| FR-12 | Lead-lag analysis | Pairwise market lead-lag relationships use aligned returns, minimum overlap and significance testing. |
| FR-13 | Influence network | Significant directed edges produce centrality/PageRank-based influence summaries. |
| FR-14 | Geographic-distance effect | Haversine pair distances are related to price-return similarity with bins and rank correlation. |
| FR-15 | Weather effect | Weather anomalies are joined to market series and event-window price/arrival responses are calculated. |
| FR-16 | Market crunch detection | Arrival collapse plus price surge events are identified from robust z-scores/thresholds. |
| FR-17 | Clickable India map | Clicking a state updates the state selection and linked charts when GeoJSON is available. |
| FR-18 | Commodity drill-down | User can select commodity, state, market and date window. |
| FR-19 | Ripple visualization | User can inspect a leader/shock and step through lagged network propagation. |
| FR-20 | Data quality page | Missingness, duplicates, reporting density and coordinate/weather coverage are displayed. |
| FR-21 | Exports | Analytical tables and figures can be exported to `outputs/`. |
| FR-22 | Tests | Unit/integration tests cover preprocessing, metrics, network direction, weather joins and app smoke import. |
| FR-23 | Resumable CEDA ingestion | Historical CEDA pulls are checkpointed by commodity×district×year, can resume after interruption, and retain failed-job records. |
| FR-24 | CEDA catalog validation | Commodity/geography catalogs can be fetched and cached before historical ingestion. |
| FR-25 | Coverage-driven scope freeze | Commodity selection exposes state/market/temporal/arrival components, threshold eligibility and recommended flags. |
| FR-26 | Empirical freeze provenance | Final analytical run records REAL/DEMO mode and configuration, and source snapshots remain auditable. |



## Phase 3 functional extensions
- **FR-P3-01** Generate and retain a unique `market_id` from normalized state, district and market.
- **FR-P3-02** Import reviewed coordinate CSVs and produce a coordinate coverage audit.
- **FR-P3-03** Provide a policy-gated, request-capped Nominatim helper for small unresolved samples only.
- **FR-P3-04** Retrieve/copy ADM1 vector boundaries with a machine-readable provenance sidecar.
- **FR-P3-05** Plan, cache, resume and rebuild NASA POWER weather by grid cell × year.
- **FR-P3-06** Compute robust seasonal weather anomalies and declustered weather-event responses.
- **FR-P3-07** Compute Haversine distance/co-movement pairs and a QAP-style permutation diagnostic.
- **FR-P3-08** Compute source-oriented network influence components.
- **FR-P3-09** Detect daily leader price shocks and visualize follower daily responses at their inferred edge lags.
- **FR-P3-10** Export state maps/networks/ripple figures through Plotly's SVG image-export control in the browser.

## Phase 4 functional extensions
- **FR-P4-01** Audit an explicitly selected commodity/date empirical scope against REAL-mode, provenance, temporal, geographic, arrival and weather coverage gates.
- **FR-P4-02** Create a new immutable-style empirical snapshot containing only the exact selected paper inputs.
- **FR-P4-03** Record SHA-256 hashes for every frozen analytical input and verify them on demand.
- **FR-P4-04** Refuse DEMO-only empirical freezes unless a testing-only override is explicitly supplied.
- **FR-P4-05** Re-estimate lead-lag networks independently by evaluable calendar year and report directed-edge persistence.
- **FR-P4-06** Report year-level source-oriented leader rankings and temporal-stability summaries.
- **FR-P4-07** Generate all paper-oriented result tables inside the freeze directory with a separate result-integrity manifest.
- **FR-P4-08** Display the latest empirical-freeze/readiness status in the local dashboard.

## Phase 5 functional extensions
- **FR-P5-01** Every normalized market observation SHALL carry a machine-readable `source_tier` in addition to `data_mode`.
- **FR-P5-02** Direct OGD ingestion SHALL be classified `PRIMARY_OFFICIAL`; CEDA API/portal data SHALL be classified `CURATED_OFFICIAL_DERIVED`.
- **FR-P5-03** Generic imports SHALL be restricted to non-paper tiers (`USER_SUPPLIED` or `SECONDARY_MIRROR`).
- **FR-P5-04** Dedicated manual OGD and CEDA importers SHALL preserve the raw file, hash it and append an ingestion-provenance record.
- **FR-P5-05** Final empirical readiness SHALL hard-fail when any selected observation comes from a non-paper source tier.
- **FR-P5-06** A `doctor` command SHALL report local empirical prerequisites without exposing secret values or making network requests.
