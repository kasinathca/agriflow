# Requirements Traceability Matrix

| Requirement | Module | Tests | UI/output |
|---|---|---|---|
| FR-08 validation | `data/processing.py` | `test_processing.py` | Data Quality |
| FR-09 coverage | `analytics/coverage.py` | `test_analytics.py` | Overview/Quality |
| FR-10 dispersion | `analytics/dispersion.py` | `test_analytics.py` | Overview/Map |
| FR-11 supply-price | `analytics/supply_price.py` | `test_analytics.py` | Weather & Crunch / exports |
| FR-12 lead-lag | `analytics/lead_lag.py` | `test_lead_lag.py` | Influence |
| FR-13 influence | `analytics/network.py` | `test_network.py` | Influence/Ripple |
| FR-14 geography | `analytics/geography.py` | `test_geography.py` | Geography |
| FR-15 weather | `analytics/weather.py` | `test_weather.py` | Weather & Crunch |
| FR-16 crunch | `analytics/events.py` | `test_weather.py` | Weather & Crunch |
| FR-17 map | `visualization/figures.py`, `ui/app.py` | smoke/manual | India Map |
| FR-21 exports | `scripts/run_analysis.py` | integration | `outputs/` |
| FR-23 resumable CEDA | `data/ceda_ingest.py`, `data/sources/ceda.py` | `test_ceda_ingest.py`, `test_sources.py` | CLI/checkpoint ledger |
| FR-24 catalog validation | `data/sources/ceda.py`, `cli.py` | `test_sources.py` | `ceda-catalog` |
| FR-25 scope freeze | `analytics/selection.py` | `test_selection.py` | Data Quality / `commodity_scope_selection.*` |
| FR-26 empirical provenance | `cli.py`, `data/ceda_ingest.py` | integration/manual | `run_manifest.json`, raw metadata |



## Phase 3 traceability additions
| Requirement | Implementation | Verification |
|---|---|---|
| FR-P3-01 | `data/identity.py`, processing, analytics | `test_phase3_identity.py` |
| FR-P3-02/03 | `data/sources/geo.py`, CLI coordinate commands | structural/CLI checks |
| FR-P3-04 | `GeographySource.download_state_geojson` | `test_phase3_geo_source.py` |
| FR-P3-05 | `data/weather_ingest.py` | `test_phase3_weather_ingest.py` |
| FR-P3-06 | `analytics/weather.py` | `test_phase3_spatial_weather.py` |
| FR-P3-07 | `analytics/geography.py` | `test_phase3_spatial_weather.py` |
| FR-P3-08 | `analytics/network.py` | `test_network.py` |
| FR-P3-09 | `analytics/events.py`, `visualization/figures.py` | demo analytical smoke test |
| FR-P3-10 | Dash Graph export config | syntax/figure smoke validation |

## Phase 4 traceability additions
| Requirement | Implementation | Verification |
|---|---|---|
| FR-P4-01 | `research/freeze.py::empirical_readiness`, CLI | `test_phase4_freeze.py` |
| FR-P4-02/03/04 | `research/freeze.py::freeze_scope/verify_freeze` | `test_phase4_freeze.py` |
| FR-P4-05/06 | `analytics/robustness.py` | `test_phase4_robustness.py` |
| FR-P4-07 | `research/runner.py` | `test_phase4_runner.py`, packaged frozen-run smoke test |
| FR-P4-08 | `ui/app.py` Research Status tab | syntax/manual dashboard acceptance |

## Phase 5 traceability additions
| Requirement | Implementation | Verification |
|---|---|---|
| FR-P5-01/02 | `data/provenance.py`, `data/processing.py`, source adapters | `test_phase5_provenance.py` |
| FR-P5-03 | `cli.py::cmd_import` and parser restrictions | parser/unit validation |
| FR-P5-04 | `data/manual_import.py`, dedicated import commands, provenance JSONL | `test_phase5_provenance.py`, CLI smoke |
| FR-P5-05 | `research/freeze.py::empirical_readiness` | `test_phase5_provenance.py`, Phase 4 regression suite |
| FR-P5-06 | `cli.py::cmd_doctor` | offline CLI smoke |
