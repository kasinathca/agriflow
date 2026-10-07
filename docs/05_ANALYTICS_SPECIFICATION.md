# Analytics Specification

## A1. Coverage audit
For each state×commodity pair compute observations, unique markets, active dates, first/last date, reporting density and arrival availability.

## A2. Price dispersion
For a date/commodity across comparable market observations:
- median price
- interquartile range (IQR)
- median absolute deviation (MAD)
- coefficient of variation (reported only when mean is suitable)
- relative price gap `(p90 - p10) / median`

## A3. Arrival-price relationship
Primary descriptive measures:
- Spearman correlation between arrivals and modal price.
- Log-log OLS: `ln(price) = α + β ln(arrivals + 1) + ε`; β is interpreted as an association/elasticity estimate, not causal supply elasticity.

## A4. Lead-lag transmission
1. Aggregate to one daily modal price per market/commodity.
2. Compute log returns `r_t = ln(P_t) - ln(P_{t-1})` on observed consecutive dates.
3. For market pair A,B, evaluate Pearson cross-correlation over lags `1..MAX_LAG_DAYS` in both directions.
4. Require `MIN_OVERLAP_DAYS` aligned observations.
5. Candidate edge A→B is the positive lag where A changes precede B and absolute correlation is maximal.
6. Test correlation; correct the family of candidate edge p-values with Benjamini-Hochberg FDR.
7. Retain edge only if `|r| >= MIN_EDGE_CORR` and `q <= FDR_ALPHA`.

This provides temporal precedence + association, not causality.

## A5. Influence / “price leader” score
On the significant directed graph:
- weighted PageRank
- normalized outgoing weighted degree
- betweenness centrality
- edge lead consistency
Composite score = weighted average of normalized components. Component values remain visible so the score is auditable.

## A6. Market integration score
For pair A,B:
- return similarity (Spearman/Pearson)
- normalized median price gap
- fraction of shared reporting dates
- transmission strength, if significant
The composite score is an exploratory index; it is not a welfare/efficiency proof.

## A7. Geographic-distance effect
- Haversine distance between market coordinates.
- Pairwise return correlation vs distance.
- Distance bins: 0–100, 100–250, 250–500, 500–1000, >1000 km.
- Spearman rank relationship between distance and similarity.

## A8. Weather anomaly
For each spatial weather cell, compute day-of-year/month climatological baseline where enough years exist, otherwise rolling robust baseline. Define standardized rainfall and temperature anomalies.

## A9. Weather event study
A severe weather event is an observation beyond configurable percentile/z-score thresholds. For each event, report price and arrival percentage changes over +1, +3, +7 and +14 days where observations exist. Results are associations and may reflect transport, policy, storage or seasonality.

## A10. Market crunch event
A market crunch candidate occurs when:
- arrivals robust-z ≤ configured negative threshold, and
- price robust-z ≥ configured positive threshold within the configured window.
The dashboard displays the raw series and thresholds for each detected event.

## A11. Ripple visualization
Given a selected leader/event date, markets are colored/sized by standardized price change at lag 0..N days. Directed network edges remain annotated with inferred lead days and strength. This is a visualization of observed statistical transmission, not a physical transport route.


## Phase 3 analytical refinements
### Source-oriented influence
For graph edge `A→B` meaning A statistically leads B, PageRank is calculated on the reversed graph to measure upstream/source centrality. Composite influence remains exploratory and includes source PageRank, normalized outbound strength, betweenness and lead-lag consistency.

### Geographic distance decay
Daily log-return co-movement is compared with Haversine distance. Since pairs share markets, the pair rows are dependent. AgriFlow therefore reports a QAP-style market-label permutation p-value in addition to the conventional Spearman diagnostic.

### Weather anomalies and event study
Weather anomalies are robust within-location, within-calendar-month z-scores. Extreme days are declustered. Responses are measured from the latest pre-event market observation to the first observed market record at/just after each response horizon. These are descriptive associations.

### Ripple snapshot
The ripple map uses a leader's observed daily price shock at date t. A follower connected by an inferred lag L displays its daily return at t+L. This matches the lead-lag statistic and is not a causal attribution.
