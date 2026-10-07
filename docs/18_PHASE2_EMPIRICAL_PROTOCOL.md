# Phase 2 Empirical Protocol and Freeze Gate

## Purpose
Phase 2 converts the verified software baseline into an empirical research pipeline. No paper-level claim may be frozen until the real-data gate below is satisfied.

## Gate 1 — Source authentication and catalog snapshot
1. Configure `CEDA_API_KEY` in `.env`.
2. Run `python -m agriflow ceda-catalog`.
3. Preserve `data/raw/ceda_catalog_commodities.csv` and `data/raw/ceda_catalog_geographies.csv` with the run date.
4. Verify the intended commodity names and state identifiers against the snapshot.

## Gate 2 — Small pilot
Run one commodity, one state and a limited number of districts for at least one complete year. Validate:
- non-empty market-level price rows;
- sensible date range;
- min ≤ modal ≤ max where fields are present;
- market names resolve from IDs;
- arrival quantity joins do not duplicate price rows;
- rerunning the same command uses cached checkpoints;
- REAL/DEMO provenance remains separated.

## Gate 3 — Candidate-panel ingestion
Expand to a broad candidate commodity set. Historical ingestion is chunked as:

`commodity × state × district × calendar-year`

Each successful chunk has a CSV and metadata checkpoint. Failed jobs are recorded in `data/raw/ceda_chunks/_errors.jsonl`; they must be reviewed before empirical freeze.

## Gate 4 — Coverage audit and commodity freeze
Run:

```bash
python -m agriflow scope-audit --target-count 10
```

The screening table reports:
- number of observed states/UTs;
- state coverage ratio within the ingested panel;
- number of markets;
- observations;
- temporal span;
- median state-level reporting density;
- arrival availability;
- transparent composite coverage score;
- threshold eligibility;
- recommended flag.

Default eligibility thresholds are intentionally conservative screening rules, not scientific constants. The final basket is frozen only after reviewing both coverage and substantive agricultural relevance.

## Gate 5 — Geographic quality
1. Generate `data/processed/markets.csv`.
2. Run geocoding on a small sample first.
3. Review all `coordinate_quality` flags.
4. District-centroid fallbacks may support coarse distance/weather analysis but must not be presented as exact mandi coordinates.

## Gate 6 — Weather alignment
Fetch NASA POWER daily weather for the frozen market coordinate panel. Verify:
- requested date range covers the market series;
- rainfall and temperature columns are populated;
- spatial-cell reuse does not duplicate market-day rows;
- missing weather is retained as missing rather than zero.

## Gate 7 — Analytical freeze
Run `python -m agriflow analyze`. Before results enter the IEEE-style paper:
- inspect `run_manifest.json` and confirm `data_mode=REAL`;
- inspect quality and coverage outputs;
- confirm significant lead-lag edges satisfy overlap/effect/FDR rules;
- confirm market influence is described as statistical leadership, not causal control;
- inspect weather/crunch events in raw series before interpretation;
- retain exact configuration and source snapshots used for the final run.

## Frozen core study period
Preferred primary study window: **2019-01-01 to 2025-12-31** because it provides complete calendar years while capturing pre-COVID, COVID-disruption and post-COVID periods. 2026 may be used as an explicitly partial recent-validation period rather than mixed into full-year seasonal comparisons.

## Reproducibility record
For every paper result, record:
- source and retrieval date;
- CEDA catalog snapshot hash;
- commodity basket;
- date window;
- market count;
- coordinate-quality distribution;
- weather source/parameters;
- analysis configuration;
- Git commit/release version.
