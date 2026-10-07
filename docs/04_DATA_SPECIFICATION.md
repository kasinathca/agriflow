# Data Specification and Provenance

## Primary market data
### A. Government of India OGD / AGMARKNET daily resource
- Dataset: Current Daily Price of Various Commodities from Various Markets (Mandi)
- Publisher: Directorate of Marketing & Inspection, Department of Agriculture & Farmers Welfare, Ministry of Agriculture & Farmers Welfare.
- Resource ID: `9ef84268-d588-465a-a308-a864a43d0070`
- Expected fields: state, district, market, commodity, variety, grade, arrival_date, min_price, max_price, modal_price.
- Use: current/recent official observations and source validation.

### B. CEDA Agri Market Data API
- Provider: Centre for Economic Data & Analysis, Ashoka University.
- Origin: cleaned access layer over AGMARKNET data.
- Current client base: `https://api.ceda.ashoka.edu.in/v1`; credential is sent as a Bearer token.
- Endpoints documented for commodities, geographies, markets, prices and quantities.
- Use: historical market-level price and arrival series where user supplies a CEDA credential or exported data.
- Raw fetch unit: commodity × state × district × calendar-year checkpoint, retaining source IDs and job metadata.

## Weather data
### C. NASA POWER Daily API
- Community: AG (Agroclimatology)
- Variables used: `PRECTOTCORR` (precipitation) and `T2M` (2 m temperature); optional max/min temperature can be enabled.
- Use: reproducible historical daily weather at market/grid coordinates.
- Important: this is gridded reanalysis/remote-sensing-derived data, not a mandi weather station measurement.

### D. India Meteorological Department (IMD)
- Use: Indian official rainfall reference/current state/district rainfall where accessible.
- Historical IMD data may require separate data-supply procedures; therefore the reproducible historical pipeline does not depend on unrestricted bulk IMD access.

## Geographic boundaries
- Preferred source: Government of India NIC/Bharat Maps ArcGIS state boundary service (GeoJSON-supported).
- Cached locally after first successful retrieval.

## Canonical price schema
| Field | Type | Unit/meaning |
|---|---|---|
| date | date | reporting date |
| state | str | normalized state/UT name |
| district | str | district |
| market | str | mandi/market |
| commodity | str | commodity |
| variety | str | variety, nullable |
| grade | str | grade, nullable |
| min_price | float | ₹/quintal when source follows AGMARKNET convention |
| max_price | float | ₹/quintal |
| modal_price | float | ₹/quintal |
| arrivals | float | source-defined quantity normalized to tonnes when documented/possible |
| source | str | provenance identifier |
| data_mode | str | REAL or DEMO |

## Missing data policy
- Missing report ≠ zero.
- No forward filling for lead-lag inference.
- Short gaps may be imputed only in explicitly labelled exploratory modules; network inference uses observed aligned dates by default.
- Variety/grade aggregation is performed by daily market median unless user filters a specific variety/grade.

## Commodity selection policy
The analytical basket is not hard-coded as a claim of national representation. Phase 2 ranks candidate commodities by observed state coverage, market breadth, observation count, temporal span, reporting density and arrival-data availability. Threshold eligibility and score components remain visible. The final basket is frozen only after this audit plus substantive agricultural relevance review. See `docs/18_PHASE2_EMPIRICAL_PROTOCOL.md`.


## Phase 3 schema extensions
### Stable market identity
`market_id = slug(state) + "__" + slug(district) + "__" + slug(market)` is the national analytical key. Source market IDs are retained separately when available.

### Coordinate table
`markets.csv` retains: `market_id, state, district, market, lat, lon, coordinate_quality, coordinate_source`.

### POWER cell mapping
`power_market_cells.csv` retains exact market coordinates plus `power_cell_lat` and `power_cell_lon`. The cell is a request/deduplication location and must not replace the actual market coordinate.

### Weather daily table
`weather_daily.csv` retains `date, market_id, market, state, district, exact market lat/lon, POWER cell, rainfall_mm, temperature_c, temperature_max_c, temperature_min_c, source, data_mode`.
