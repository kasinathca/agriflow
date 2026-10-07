# AgriFlow — Project Charter

## Project title
**AgriFlow: Spatiotemporal Analysis of Price Transmission, Weather Shocks, and Market Integration Across Indian Agricultural Mandis**

## Course context
CSI3004 — Data Science Programming, academic project.

## Team
- Kasinath C A — 24MID0124
- Kamal Nayan C S — 24MID0189

## Problem
Wholesale agricultural prices can differ substantially across locations and time. Daily mandi prices and arrivals are available through AGMARKNET-derived sources, while weather data can be obtained from government and scientific public datasets. However, these sources are rarely combined into a reproducible analytical system that quantifies market integration, identifies statistically influential price-leading markets, relates supply shocks and weather anomalies to price movements, and presents the findings geographically.

## Primary research question
How integrated are Indian agricultural wholesale markets, how do price/supply/weather shocks propagate between them, and which markets show statistically significant price leadership or persistent isolation for particular commodities?

## Scope frozen for Version 1
1. Pan-India-ready ingestion architecture with analysis limited by actual reporting coverage.
2. Commodity basket selected by a formal coverage audit rather than by assumption.
3. Daily modal price as the primary price variable; min/max retained for quality checks.
4. Arrival quantity where available.
5. Geographic-distance effects using market/district coordinates and Haversine distance.
6. Weather integration using daily rainfall and temperature; NASA POWER is the reproducible historical API path, with IMD used as an Indian official validation/reference source where available.
7. Price dispersion, supply-price association, lead-lag transmission, network influence, market integration, weather-shock event studies, and market-crunch detection.
8. Local interactive Dash application with clickable India state map, state drill-down, network/ripple views, weather/price overlays and methodology/data-quality pages.
9. Export of tables/figures suitable for an IEEE-style report.

## Explicit non-goals for Version 1
- Claiming causal control of one mandi over another.
- Producing trading advice or farmer price guarantees.
- Treating missing reports as zero arrivals or zero prices.
- Hiding sparse/uneven state coverage.
- Building a cloud deployment as a prerequisite for demonstration.

## Success criteria
The project is successful if a fresh machine can install dependencies through the supplied bootstrap scripts, launch a fully functional demonstration dataset without credentials, optionally switch to real public-source data through documented credentials/imports, run the analytical pipeline deterministically, pass automated tests, and expose all major analytical outputs through the local dashboard.
