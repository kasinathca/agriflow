# CEDA Historical Ingestion Protocol

## Interface
Base: `https://api.ceda.ashoka.edu.in/v1`

Endpoints used:
- `GET /agmarknet/commodities`
- `GET /agmarknet/geographies`
- `POST /agmarknet/markets`
- `POST /agmarknet/prices`
- `POST /agmarknet/quantities`

AgriFlow sends the configured CEDA credential as `Authorization: Bearer <token>`.

## Why ingestion is resumable
A national multi-commodity study can require many independent district/date requests and may encounter rate limiting or transient failures. A monolithic request would be difficult to audit and expensive to restart. AgriFlow therefore checkpoints one commodity × district × calendar-year job.

## Raw checkpoint contents
Each chunk CSV retains canonical names plus source IDs:
- source commodity ID;
- source state ID;
- source district ID;
- source market ID;
- prices;
- arrival quantity where returned;
- source and data mode.

A paired `.meta.json` stores the job specification, completion time, row count and whether quantities were requested.

## Resume semantics
- Completed CSV + metadata pair: skipped by default.
- `--force`: refetches completed jobs.
- failed jobs: recorded in `_errors.jsonl` and do not silently appear as successful zero-row coverage.
- truly empty successful calls: checkpointed as empty so they are not repeatedly queried.

## Dry-run
`--dry-run` builds the exact job plan without making price/quantity calls. Use it before any large pull.

## Arrival quantities
CEDA's quantity endpoint is merged to price observations using date + commodity/state/district/market IDs. If quantity retrieval fails temporarily, price data remains usable and arrivals stay missing. Missing arrival does not mean zero arrival.

## Rebuilding the panel
After successful jobs, all non-empty chunk CSVs are normalized and aggregated to one comparable market/commodity/day record. The processed table is written to:

`data/processed/market_daily.csv`

The market coordinate index is refreshed without overwriting previously resolved coordinates.

## Operational examples
```bash
python -m agriflow ceda-catalog

python -m agriflow fetch-ceda --commodity Onion --state Maharashtra \
  --start 2024-01-01 --end 2024-12-31 --district-limit 2 --dry-run

python -m agriflow fetch-ceda --commodity Onion --state Maharashtra \
  --start 2024-01-01 --end 2024-12-31 --district-limit 2
```

For pan-India expansion, omit `--state` only after the pilot succeeds. Multiple commodities may be supplied by repeated `--commodity` arguments or comma-separated values.
