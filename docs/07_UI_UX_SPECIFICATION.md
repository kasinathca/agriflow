# Dashboard / UX Specification

## Visual standard
Professional academic dashboard: off-white background, navy typography, restrained green accent, no decorative gradients, no misleading 3D charts. Font stack: Inter/Segoe UI/Arial system fallback.

## Global controls
- Data mode badge
- Commodity selector
- State selector
- Market selector (context-sensitive)
- Date range selector

## Tabs
1. **Overview** — KPIs, coverage, national price trend, data provenance.
2. **India Map** — state choropleth; click state to drill down; linked state trend and top markets.
3. **Market Influence** — significant directed leader/follower graph, influence table, edge lag/correlation/q-value.
4. **Weather & Crunch** — rainfall/temperature anomalies over price/arrivals; event list; lag response chart.
5. **Geography** — distance vs return similarity, distance-bin summary.
6. **Data Quality** — missingness, invalid-price checks, coordinate/weather coverage and state×commodity coverage.
7. **Methods** — definitions, thresholds, caveats, source links.

## Accessibility/integrity
- Tooltips contain units and dates.
- Demo mode is visually persistent.
- Empty/insufficient results display a reason.
- Network edges never use the word “causal”.


## Phase 3 UI refinements
- Market selectors display human-readable `Market — District, State` labels but store `market_id` values.
- India state visualization is vector-based and clickable; the Plotly camera control is configured for SVG export.
- Market Influence explicitly explains source-oriented centrality.
- Ripple explorer defaults to a detected leader shock when available and displays follower responses at inferred lags.
- Geography presents the QAP-style permutation statistic as the primary significance diagnostic.
- Weather presents a declustered event-response chart beside the market timeline and crunch candidates.
