# Software Requirements Specification (SRS)

## 1. Purpose
AgriFlow is a reproducible data-science application for exploring spatial and temporal relationships in Indian agricultural mandi prices, arrivals, weather and geography.

## 2. User classes
- **Student/researcher:** configures data, runs pipeline, validates methods and exports results.
- **Faculty/reviewer:** explores results through a local dashboard without editing code.
- **Developer:** extends connectors, analytical methods, tests and visualizations.

## 3. System boundary
The system consists of data connectors/importers, validation/preprocessing, analytical modules, cached processed datasets, a Dash web interface and export utilities. External data providers remain outside the system boundary.

## 4. Functional requirements
See `02_FUNCTIONAL_REQUIREMENTS.md` for atomic IDs.

## 5. Non-functional requirements
See `03_NON_FUNCTIONAL_REQUIREMENTS.md`.

## 6. Data requirements
See `04_DATA_SPECIFICATION.md`.

## 7. Analytical requirements
See `05_ANALYTICS_SPECIFICATION.md`.

## 8. Interface requirements
- Local HTTP dashboard, default `http://127.0.0.1:8050`.
- CLI for data setup, validation, analysis and export.
- `.env` configuration for optional API credentials.
- CSV imports/exports plus resumable CEDA raw checkpoints.

## 9. Failure behavior
- Network/API failure must not crash the demonstration mode.
- Long-running historical CEDA ingestion must checkpoint completed jobs so interrupted pulls can resume safely.
- Real-data mode must never silently substitute synthetic observations.
- Every figure must expose data mode (`DEMO` or `REAL`) and latest data date where relevant.
- Inadequate sample sizes must produce a visible “insufficient data” result, not a fabricated statistic.

## 10. Constraints
- Python 3.10+.
- Local-first execution.
- No paid service required for the demonstration.
- Public-source attribution must be preserved.


## Phase 3 frozen requirements (v1.2)
- All national market-level joins SHALL use a stable pan-India market identifier; display names alone SHALL NOT be treated as globally unique.
- The system SHALL support reviewed market-coordinate imports and SHALL preserve coordinate quality/source metadata.
- Public Nominatim use SHALL require explicit acknowledgement of its usage policy and SHALL be capped/throttled for small one-time batches.
- Historical NASA POWER weather acquisition SHALL be resumable and deduplicated to approximately the documented meteorological source-grid resolution.
- The system SHALL provide a clickable vector India state map and browser-side SVG export where Plotly supports it.
- Geographic-distance analysis SHALL expose a permutation-based significance diagnostic suitable for dependent market-pair matrices.
- Weather-event analyses SHALL decluster adjacent extreme-weather days and retain actual baseline/response dates.
- Price-leadership scoring SHALL be source-oriented and SHALL NOT use sink-oriented PageRank without directional correction.
- Ripple visualizations SHALL show edge-aligned follower responses at inferred lags and SHALL retain a non-causal interpretation warning.
