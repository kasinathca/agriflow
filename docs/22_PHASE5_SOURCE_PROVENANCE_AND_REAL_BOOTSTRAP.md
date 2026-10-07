# Phase 5 — Source Provenance and Real-Data Bootstrap Protocol

## Purpose
Phase 5 hardens the boundary between **real observations** and **paper-acceptable evidence**. A row can be non-synthetic (`REAL`) while still coming from a secondary mirror or an unverified user file. AgriFlow therefore records both `data_mode` and `source_tier`.

## Source-tier vocabulary
| Tier | Meaning | Final-paper freeze? |
|---|---|---|
| `PRIMARY_OFFICIAL` | Direct Government of India OGD/AGMARKNET observation or a manually downloaded official OGD export retained with provenance. | Yes |
| `CURATED_OFFICIAL_DERIVED` | CEDA Agri-Market data derived from AGMARKNET, obtained through the documented API or a retained CEDA portal export. | Yes |
| `SECONDARY_MIRROR` | Third-party archive/mirror that states it reproduces an official feed. Useful for bootstrap/testing only. | No |
| `USER_SUPPLIED` | Generic local CSV whose authoritative origin has not been established by a dedicated importer. | No |
| `DEMO` | Deterministic synthetic verification data. | No |
| `UNKNOWN` | Missing/unclassified provenance. | No |

A final empirical freeze passes the new `paper_acceptable_source_tier` hard gate only when all selected observations are from `PRIMARY_OFFICIAL` and/or `CURATED_OFFICIAL_DERIVED` tiers.

## Official-source import paths
### Direct API
```bash
python -m agriflow fetch-current --state Maharashtra --commodity Onion --max-records 5000
python -m agriflow fetch-ceda --commodity Onion --state Maharashtra --start 2023-01-01 --end 2025-12-31
```

### Manual CEDA portal export
If the API credential is not yet available, download a market-level CSV from the CEDA Agri-Market portal and retain the exact portal filters/date range in your project notes.

```bash
python -m agriflow import-ceda-csv ceda_onion_lasalgaon.csv \
  --state Maharashtra --district Nashik --market Lasalgaon --commodity Onion
```

### Manual Government OGD export
```bash
python -m agriflow import-data-gov-csv agmarknet_export.csv \
  --state Maharashtra --district Nashik --market Lasalgaon --commodity Onion
```

The dedicated importers use schema-tolerant column mapping, hash and retain the raw file, write an `ingest_provenance.jsonl` record, and assign the appropriate source tier. They do not invent missing market/commodity identity.

## Generic/secondary data
A generic file may be imported only as `USER_SUPPLIED` or `SECONDARY_MIRROR`:

```bash
python -m agriflow import-prices bootstrap.csv --source BOOTSTRAP_ARCHIVE --source-tier SECONDARY_MIRROR
```

Such data can be used for software tests, exploratory plots and pipeline debugging, but the final paper freeze intentionally rejects it.

## Environment doctor
Before a real run:

```bash
python -m agriflow doctor
```

The command performs no network requests and reports:
- whether CEDA/data.gov.in credentials are configured (never their values);
- whether REAL processed market data exists;
- observed source tiers;
- record/state/market/commodity/date coverage;
- coordinate and weather availability;
- latest freeze integrity status when present;
- next-action recommendations.

The report is saved to `outputs/doctor_report.json`.

## Provenance record
Every dedicated real-data ingestion/import appends a JSON line to:

`data/raw/ingest_provenance.jsonl`

Each record contains source label, source tier, row count, retained raw-file path, raw-file SHA-256 and an explanatory note. This file is intended to be copied into a final empirical freeze provenance bundle.

## Paper rule
`REAL` is necessary but not sufficient. Final numerical claims must satisfy all of the following:
1. `data_mode == REAL`;
2. source tier is paper-acceptable;
3. readiness gates have been reviewed;
4. selected input files are frozen and SHA-256 verified;
5. the reported result comes from the freeze-local analysis outputs.
