# AgriFlow

**Release:** v1.4.0 — provenance-gated real-data bootstrap

**Spatiotemporal Analysis of Price Transmission, Weather Shocks, and Market Integration Across Indian Agricultural Mandis**

Academic Data Science project by **Kasinath C A (24MID0124)** and **Kamal Nayan C S (24MID0189)**.

AgriFlow is a local-first analytical system for studying agricultural wholesale price dispersion, arrivals, geographic market integration, statistically inferred price leadership, weather-linked shocks and market crunches across India. It is intentionally not a generic next-day price-prediction dashboard.

> **Academic-integrity rule:** the zero-credential demonstration uses deterministic synthetic data and is permanently labelled `DEMO`. Demo numbers are software-verification fixtures, not empirical findings. Final report results must be regenerated in `REAL` mode from frozen public-source data.

## 1. One-time setup

### Windows
```bat
setup.bat
```
Later launches:
```bat
run.bat
```

### Linux/macOS
```bash
chmod +x setup.sh run.sh
./setup.sh
./run.sh
```

First run verifies Python 3.10+, creates `.venv`, installs dependencies, creates `.env`, generates deterministic demo data, attempts to cache an India ADM1 vector boundary, runs the analytical export pipeline and executes the automated test suite.

Open **http://127.0.0.1:8050** after launching.

## 2. Dashboard

- **Overview** — national/state price trends, arrivals-price association and reporting coverage.
- **India Map** — clickable vector state choropleth. Use Plotly's camera icon to export the map as **SVG**.
- **Market Influence** — FDR-filtered daily-return lead/lag network and source-oriented influence ranking.
- **Price-shock Ripple** — leader daily shock plus follower daily responses at their own inferred edge lags.
- **Weather & Crunch** — price/rain/temperature timelines, declustered weather-event response chart and simultaneous low-arrival/high-price crunch candidates.
- **Geography** — distance versus daily-return co-movement, plus QAP-style market-label permutation significance.
- **Data Quality** — reporting density, missing arrivals and coverage-driven commodity selection.
- **Research Status** — latest frozen empirical scope, readiness gates and academic-integrity status.
- **Methods & Sources** — provenance and interpretation guardrails.

## 3. Core data sources

### Government of India OGD / AGMARKNET — current mandi prices
Resource:
`https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070`

Catalog page:
`https://data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi`

Optional `.env` key:
```env
DATA_GOV_API_KEY=your_key_here
```

Example:
```bash
python -m agriflow fetch-current --state Maharashtra --commodity Onion --max-records 5000
```

### CEDA Agri Market Data — historical AGMARKNET prices and arrivals
Documentation:
`https://api.ceda.ashoka.edu.in/documentation/`

AgriFlow targets the documented `/v1/agmarknet` commodity, geography, market, price and quantity paths with Bearer authentication.

```env
CEDA_API_KEY=your_token_here
```

Validate first:
```bash
python -m agriflow ceda-catalog
```

Pilot before national acquisition:
```bash
python -m agriflow fetch-ceda --commodity Onion --state Maharashtra \
  --start 2024-01-01 --end 2024-12-31 --district-limit 2 --dry-run

python -m agriflow fetch-ceda --commodity Onion --state Maharashtra \
  --start 2024-01-01 --end 2024-12-31 --district-limit 2
```

Historical CEDA acquisition is resumable by **commodity × district × calendar year**. Completed checkpoints are skipped unless `--force` is used.

If API credentials are unavailable, use the **dedicated** manual-export routes so provenance cannot be self-declared:
```bash
# CSV downloaded from the CEDA Agri-Market portal
python -m agriflow import-ceda-csv path/to/ceda_export.csv \
  --state Maharashtra --commodity Onion

# CSV downloaded from the official Government OGD / AGMARKNET resource
python -m agriflow import-data-gov-csv path/to/ogd_export.csv
```

Generic external CSVs use `import-prices` and are deliberately classified only as `USER_SUPPLIED` or `SECONDARY_MIRROR`; they can support exploration, but cannot pass the final-paper source-authority gate.


### Source-authority tiers
Every processed market record carries a `source_tier`:

| Tier | Typical source | Final-paper freeze |
|---|---|---:|
| `PRIMARY_OFFICIAL` | Government of India OGD / AGMARKNET | Allowed |
| `CURATED_OFFICIAL_DERIVED` | CEDA Agri-Market data derived from AGMARKNET | Allowed |
| `SECONDARY_MIRROR` | third-party mirrors / archives | Blocked |
| `USER_SUPPLIED` | generic local CSV import | Blocked |
| `DEMO` | deterministic fixture | Blocked |

This is a hard integrity rule: naming a generic CSV “official” does not promote it. Official/curated imports have separate commands, raw-source retention, SHA-256 hashes and an append-only `data/raw/ingest_provenance.jsonl` record. That ledger is copied into empirical freezes when present.

Run an offline health check at any time:
```bash
python -m agriflow doctor
```
`doctor` reports credentials as booleans only (never their values), current data mode, source tiers, coverage, coordinate/weather readiness and latest-freeze integrity.

### NASA POWER — historical gridded weather
Daily API:
`https://power.larc.nasa.gov/docs/services/api/temporal/daily/`

NASA request guidance documents meteorological products at approximately **0.5° × 0.625°** source resolution. AgriFlow therefore deduplicates nearby markets into approximate POWER cells and checkpoints **cell × calendar-year** requests.

Parameters:
- `PRECTOTCORR`
- `T2M`
- `T2M_MAX`
- `T2M_MIN`

Plan before fetching:
```bash
python -m agriflow fetch-weather --start 2019-01-01 --end 2025-12-31 --dry-run
```

Fetch/resume:
```bash
python -m agriflow fetch-weather --start 2019-01-01 --end 2025-12-31
```

POWER values are **gridded meteorological estimates**, not observations from weather stations located at the mandis.

### IMD rainfall reference
`https://mausam.imd.gov.in/api/statewise_rainfall_api.php`

IMD remains the official Indian rainfall-reference path. AgriFlow uses NASA POWER for reproducible bulk historical weather where a uniform historical IMD acquisition route is unavailable to the project.

### India vector boundaries
Run:
```bash
python -m agriflow fetch-geojson
```

AgriFlow writes both:
- `data/cache/india_states.geojson`
- `data/cache/india_states.source.json`

Provider logic:
1. NIC/BharatMaps is attempted when its endpoint/access is usable;
2. geoBoundaries **gbOpen India ADM1** is the reproducible open fallback.

geoBoundaries API:
`https://www.geoboundaries.org/api.html`

The gbOpen product is CC BY 4.0 and requires attribution. BharatMaps service access may require Indian-government institutional authorization; AgriFlow does not assume unrestricted production access.

## 4. Market coordinates

A pan-India market is identified by:

```text
market_id = slug(state) + "__" + slug(district) + "__" + slug(market)
```

This prevents same-named mandis in different states from being merged silently.

### Preferred: reviewed coordinate import
Prepare a CSV containing either `market_id,lat,lon` or `state,district,market,lat,lon`, then:

```bash
python -m agriflow import-coordinates market_coordinates.csv \
  --source REVIEWED_ACADEMIC_COORDINATES --quality reviewed_exact
```

Coordinates are range-validated and a coverage audit is written to `outputs/coordinate_import_audit.csv`.

### Optional small Nominatim validation helper
The public OpenStreetMap Foundation Nominatim service discourages bulk geocoding and limits heavy use. Read:
`https://operations.osmfoundation.org/policies/nominatim/`

AgriFlow requires explicit acknowledgement and caps requests:
```bash
python -m agriflow geocode-markets --limit 20 --max-requests 40 --accept-nominatim-policy
```

Do **not** use that command as an unattended pan-India bulk geocoder. Use reviewed coordinates, an approved provider or a self-hosted geocoder for larger requirements.

## 5. Recommended empirical workflow

```bash
# A. Setup and validate the CEDA catalog
python -m agriflow ceda-catalog

# B. Pilot historical data
python -m agriflow fetch-ceda --commodity Onion --state Maharashtra \
  --start 2023-01-01 --end 2025-12-31 --district-limit 3 --dry-run
python -m agriflow fetch-ceda --commodity Onion --state Maharashtra \
  --start 2023-01-01 --end 2025-12-31 --district-limit 3

# C. Expand only after the pilot passes; then audit candidate commodities
python -m agriflow scope-audit --target-count 10

# D. Freeze the commodity basket after reviewing
# outputs/commodity_scope_selection.csv
# outputs/commodity_scope_selection.json

# E. Import/review market coordinates
python -m agriflow import-coordinates market_coordinates.csv

# F. Inspect weather job count before network calls
python -m agriflow fetch-weather --start 2019-01-01 --end 2025-12-31 --dry-run
python -m agriflow fetch-weather --start 2019-01-01 --end 2025-12-31

# G. Regenerate all reproducible analytical outputs
python -m agriflow analyze

# H. Audit the exact paper scope before freezing
python -m agriflow readiness-audit --commodity Onion --start 2019-01-01 --end 2025-12-31

# I. Freeze immutable-style paper inputs and verify their SHA-256 hashes
python -m agriflow freeze-scope --commodity Onion --start 2019-01-01 --end 2025-12-31 --label paper-v1
python -m agriflow verify-freeze outputs/freezes/<freeze-directory>

# J. Generate paper-oriented outputs + yearly temporal-robustness diagnostics
python -m agriflow analyze-freeze outputs/freezes/<freeze-directory>

# K. Launch the local demonstrator
python -m agriflow run
```

Final numerical claims should come from a verified directory under `outputs/freezes/`, not from mutable exploratory outputs. Each freeze contains the exact market/weather/coordinate subset, a readiness report, SHA-256 checksums and a freeze-local result manifest.

## 6. Analytical safeguards

- Network inference uses **daily log-price returns**, not raw price levels.
- Non-consecutive reporting gaps are not treated as daily returns.
- Edges require minimum overlap, minimum effect size and Benjamini–Hochberg FDR-adjusted significance.
- “Price leader” means statistical temporal leadership, **not causal or commercial control**.
- Standard PageRank would reward incoming links in a leader→follower graph, so AgriFlow uses **source-oriented PageRank on the reversed graph**.
- Market-pair rows are dependent; distance analysis therefore reports a **QAP-style label-permutation p-value** rather than relying only on a naïve correlation p-value.
- Weather extremes are declustered before event analysis.
- Weather-event and market-crunch results are descriptive associations, not causal estimates.
- Ripple markers show follower **daily returns at inferred edge lags**, matching the lead/lag statistic instead of implying an arbitrary cumulative propagation effect.
- Haversine distance is not road distance, travel time or logistics cost.
- Missing reports are never interpreted as zero arrivals.
- Final-paper analysis is executed from a named checksum-protected empirical freeze, not mutable working files.
- Price-leader claims are accompanied by independent calendar-year edge/rank stability diagnostics; a pooled-period winner is not automatically called persistent.

See `docs/05_ANALYTICS_SPECIFICATION.md`, `docs/12_VALIDATION_AND_LIMITATIONS.md`, `docs/20_PHASE3_SPATIAL_WEATHER_PROTOCOL.md`, `docs/21_PHASE4_EMPIRICAL_FREEZE_PROTOCOL.md` and `docs/22_PHASE5_SOURCE_PROVENANCE_AND_REAL_BOOTSTRAP.md`.

## 7. Reproducible outputs

`python -m agriflow analyze` generates, per commodity where possible:
- lead-lag edge table;
- influence table;
- market-integration table;
- distance-pair table;
- distance-effect JSON summary;
- weather-event rows;
- weather-event response summary;
- market-crunch candidate table;
- data quality and coverage outputs;
- run manifest with data mode and analysis settings.

`analyze-freeze` additionally produces yearly edge/leader stability tables, a freeze-local empirical summary and a SHA-256 result manifest.

## 8. Project structure

```text
AgriFlow_Project/
├─ docs/                         # SRS, requirements, protocols, ADRs, risk, traceability
├─ src/agriflow/
│  ├─ analytics/                 # coverage, network, integration, geography, weather, events
│  ├─ data/sources/              # OGD, CEDA, POWER, IMD, geography
│  ├─ data/                      # identity, preprocessing, resumable ingestion, repository, demo
│  ├─ research/                  # empirical readiness, freeze integrity, frozen-run analysis
│  ├─ visualization/             # Plotly vector/analytical figures
│  └─ ui/                        # Dash localhost application
├─ tests/                        # unit and known-answer regression tests
├─ data/                         # demo/raw/processed/cache
├─ outputs/                      # reproducible generated results
├─ .github/workflows/ci.yml
├─ setup.bat / setup.sh
└─ run.bat / run.sh
```

## 9. Verification

```bash
pytest -q
python scripts/validate_project.py
```

v1.4 contains **41 automated tests**, including known-answer tests for a two-day price leader, duplicate market names across states, POWER checkpoint/rebuild behavior, spatial permutation stability, weather-event declustering, vector-boundary provenance, empirical-freeze tamper detection and multi-year leadership persistence.

## 10. Documentation order

Engineering was preceded by and remains traceable to the project charter, SRS, functional and non-functional requirements, data specification, analytical specification, architecture, UI/UX specification, test plan, risk register, traceability matrix, ADRs, validation limitations, deployment runbook, IEEE report outline, Phase 2 empirical protocol, CEDA ingestion protocol, Phase 3 spatial/weather protocol, Phase 4 empirical-freeze/robustness protocol, and Phase 5 source-provenance/real-data bootstrap protocol.

## 11. License and source attribution

AgriFlow source code is MIT licensed. External datasets, geospatial data and services retain their own licences/terms. Preserve their attribution in the dashboard, report and presentation.
