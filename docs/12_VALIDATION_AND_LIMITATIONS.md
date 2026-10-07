# Validation and Interpretation Limits

- **Temporal precedence is not causation.** A significant A→B lead-lag edge means A's observed price changes tend to precede correlated changes in B under the chosen method.
- **Market prices are heterogeneous.** Variety, grade, quality, market rules, storage and transport conditions can produce legitimate differences.
- **Reporting gaps are informative but dangerous.** Missing data can correlate with institutional or regional factors; absence is never treated as zero.
- **Weather is spatially approximated.** NASA POWER values represent a grid cell and are not equivalent to a specific mandi weather station.
- **Distance is not transport cost.** Straight-line Haversine distance is a geographic proxy; roads, terrain, tolls and logistics differ.
- **Multiple testing is controlled, not eliminated.** FDR correction reduces false discoveries but cannot prove economic mechanism.
- **Composite scores are exploratory.** Influence and integration scores must be read with their components, not as absolute truth.


## Phase 3 limitations
- NASA POWER meteorology is gridded (~0.5° × 0.625° source resolution), not a weather station located inside each mandi.
- Market coordinates may be exact, geocoded or district-centroid approximations; `coordinate_quality` must accompany interpretation.
- geoBoundaries is an open visualization fallback and must be attributed; BharatMaps institutional service rules may restrict direct use.
- The QAP-style spatial permutation test reduces pair-dependence concerns but does not control every spatial/economic confounder.
- Weather event studies are descriptive and can be confounded by storage, transport, policy, quality, seasonality and unobserved supply conditions.
- Lead-lag edges and ripple snapshots show statistical temporal patterns, not causal market control.
