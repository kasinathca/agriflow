# Architecture

```text
Public APIs / imports
  ├─ data.gov.in AGMARKNET
  ├─ CEDA historical AGMARKNET
  ├─ NASA POWER weather
  ├─ IMD reference rainfall
  └─ NIC/Bharat Maps state geometry
            │
            ▼
      Connector adapters
            │ raw snapshots + provenance
            ├─ CEDA catalog snapshots
            └─ resumable district-year checkpoints
            ▼
   Validation / normalization
            │
            ├─ processed market daily table
            ├─ weather daily table
            ├─ market coordinate table
            └─ GeoJSON cache
            │
            ▼
       Analytics modules
 coverage/scope-freeze ─ dispersion ─ supply/price ─ lead/lag/network
 geography ─ weather events ─ crunch detection ─ integration
            │
            ▼
       Dash presentation
 overview | map | influence | weather/crunch | geography | quality | methods
            │
            ▼
     CSV/HTML/PNG exports
```

## Key architectural decisions
- **Dash + Plotly:** native interactive callbacks and SVG/WebGL visualizations suitable for local demonstration.
- **Pandas first:** dataset sizes used in class demonstrations are manageable and keep the code inspectable; large historical pulls can be processed in chunks.
- **CSV/Parquet-ready repository:** avoids requiring a database server. Optional Parquet support can be added transparently.
- **Adapter pattern:** each external source is isolated behind a connector, preventing API changes from contaminating analytics.
- **Strict demo/real separation:** app never silently mixes synthetic fixtures into empirical results.

## Phase 2 ingestion rule
Historical CEDA acquisition is deliberately separated from analytics. Long-running network calls terminate at immutable/cached raw chunk files; `market_daily.csv` is rebuilt deterministically from completed chunks. This prevents partial API failure from silently changing analytical semantics.


## Phase 3 architecture extension
A new spatial/weather acquisition layer sits beside CEDA ingestion: `market identity → coordinate registry → POWER grid-cell registry → resumable cell-year weather chunks → joined analytical panel`. State vector boundaries are independently cached with provenance for UI rendering.
