# Generated analytical outputs

This directory is intentionally source-clean in Git/release archives. `python -m agriflow analyze` regenerates the analytical outputs from the active dataset.

Important files include:
- `run_manifest.json` — data mode and analysis settings;
- `coverage_audit.csv` and commodity scope files;
- `lead_lag_<commodity>.csv` — significant candidate transmission edges;
- `influence_<commodity>.csv` — source-oriented market influence components;
- `integration_<commodity>.csv` — pairwise market-integration components;
- `distance_pairs_<commodity>.csv` / `distance_summary_<commodity>.json` — spatial co-movement and QAP-style permutation summary;
- `weather_events_<commodity>.csv` / `weather_event_summary_<commodity>.csv` — declustered descriptive weather-event responses;
- `market_crunch_candidates.csv` — simultaneous robust low-arrival/high-price anomalies.

If `data_mode` is `DEMO`, all numerical outputs are synthetic software-verification fixtures and must not be reported as empirical findings.


## Paper-grade frozen outputs

Use `readiness-audit` before final analysis. `freeze-scope` creates a timestamped directory under `outputs/freezes/` with exact analytical inputs, readiness metadata, `freeze_manifest.json` and `SHA256SUMS.txt`. Run `verify-freeze` before `analyze-freeze`. Frozen-run results include yearly edge/leader stability tables and their own `results_manifest.json`.
