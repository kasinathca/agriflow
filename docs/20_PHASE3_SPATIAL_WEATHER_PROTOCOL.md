# Phase 3 Protocol — Spatial, Weather and Ripple Analysis

## Purpose
Phase 3 converts the empirical mandi panel into a spatially explicit, weather-aware research dataset without overstating causality. This protocol is mandatory before final-paper figures are frozen.

## 1. Market identity gate
Every market must have a stable `market_id` derived from normalized `state + district + market`. Display names are not globally unique and must never be used as a national primary key.

Acceptance checks:
- no two distinct state/district/market tuples share one `market_id`;
- every lead-lag/network/coordinate/weather table retains `market_id`;
- display names may repeat, IDs may not.

## 2. Coordinate gate
Preferred order:
1. reviewed coordinate table imported with `agriflow import-coordinates`;
2. approved institutional/self-hosted geocoder;
3. public Nominatim only for a small one-time validation batch after explicitly accepting its usage policy.

Coordinate quality must be retained (`reviewed_exact`, `market_geocode`, `district_centroid`, etc.). District-centroid fallbacks are not equivalent to exact mandi coordinates and must be flagged in maps and limitations.

## 3. State vector boundary provenance
The application caches an ADM1 vector GeoJSON plus `india_states.source.json`.
- NIC/BharatMaps is attempted only when the public endpoint is usable/authorized.
- geoBoundaries gbOpen ADM1 is the reproducible open fallback and requires CC BY 4.0 attribution.

The map is an analytical visualization boundary, not evidence about disputed boundary claims.

## 4. NASA POWER weather acquisition
Source: NASA POWER Daily API, Agroclimatology community.
Parameters:
- `PRECTOTCORR` precipitation;
- `T2M` mean 2 m air temperature;
- `T2M_MAX` daily maximum;
- `T2M_MIN` daily minimum.

NASA POWER documents meteorological products at approximately 0.5° × 0.625° source resolution. AgriFlow therefore maps nearby markets to a common POWER request cell and checkpoints one cell × year request. Exact market coordinates are preserved separately.

Never describe POWER values as measurements from the mandi itself; they are gridded meteorological estimates.

## 5. Weather anomaly definition
Weather anomalies are robust z-scores calculated within market/location and calendar month. `climatology_n` is retained. Multi-year history is preferred; short climatologies must be called out in limitations.

## 6. Weather-event study
Candidate event days satisfy `|weather anomaly z| >= 2` by default. Consecutive extreme days are declustered so one weather episode is not counted as several independent events.

For each event:
- baseline = latest observed market record before the event;
- response horizons = +1, +3, +7, +14 calendar days by default;
- if the exact response day is missing, the first observation within a short tolerance window may be used and the actual response date is retained;
- report event counts and median price/arrival responses.

This is descriptive event analysis. It does not identify a causal weather effect.

## 7. Geographic-distance effect
Distance = Haversine great-circle distance between retained market coordinates.
Outcome = correlation of aligned daily log-price returns.

Because market-pair observations share nodes and are not independent, the conventional correlation p-value is not the primary inferential statistic. AgriFlow also performs a QAP-style market-label permutation test. Report:
- number of usable pairs;
- Spearman rho(distance, return correlation);
- QAP-style permutation p-value;
- distance-bin descriptive summaries.

Do not equate great-circle distance with travel time, road distance or transport cost.

## 8. Price-leadership network
Edges are based on daily log-price return lead/lag association, temporal precedence, minimum overlap, minimum effect size and Benjamini–Hochberg FDR correction.

Influence ranking uses **source-oriented PageRank on the reversed graph** plus outbound edge strength, betweenness and lag consistency. This prevents standard PageRank from automatically rewarding downstream followers in a leader→follower graph.

The phrase “price leader” means statistical temporal leadership/influence only, not legal, commercial or causal control of a commodity.

## 9. Ripple visualization
A ripple view is anchored to an observed leader daily price shock. For each significant outgoing edge with inferred lag `L`, the follower marker shows the follower's daily price return at `event_date + L`.

This mirrors the statistic used to infer the edge. It does **not** claim that the leader caused the follower movement. The map must display the interpretation guardrail alongside the figure.

## 10. Market crunch
A candidate crunch requires both:
- robust low-arrival anomaly;
- robust high-price anomaly.

A combined severity score is used only for ranking candidates. Raw price, arrivals and z-scores remain visible.

## 11. Freeze outputs
Before final report figures:
- `data/processed/markets.csv`
- `data/processed/power_market_cells.csv`
- `data/processed/weather_daily.csv`
- `outputs/distance_pairs_<commodity>.csv`
- `outputs/distance_summary_<commodity>.json`
- `outputs/weather_events_<commodity>.csv`
- `outputs/weather_event_summary_<commodity>.csv`
- `outputs/lead_lag_<commodity>.csv`
- `outputs/influence_<commodity>.csv`

must be archived together with the run manifest and source/provenance files.
