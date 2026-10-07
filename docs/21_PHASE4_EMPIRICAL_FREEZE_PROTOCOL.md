# Phase 4 Protocol — Empirical Freeze, Robustness and Paper-Grade Runs

## Purpose
Phase 4 separates exploratory analysis from evidence that may be quoted in the final report. A dashboard filter state is not a reproducible experiment. Every paper-grade result must therefore be generated from a named, checksum-protected snapshot of the exact market, coordinate and weather inputs used.

## 1. Preconditions
Before a REAL empirical freeze:
1. CEDA/AGMARKNET historical data have been acquired or a provenance-documented export has been imported.
2. `scope-audit` has been reviewed and the commodity basket is explicitly accepted.
3. The date window is explicitly stated; it must not be inherited silently from whatever data are currently present.
4. Market coordinates are reviewed to the extent required for spatial claims.
5. NASA POWER weather has been acquired for the same market/date scope if weather claims are planned.

## 2. Readiness gate
Run:

```bash
python -m agriflow readiness-audit --commodity Onion --start 2019-01-01 --end 2025-12-31
```

The audit checks:
- REAL-only data mode;
- non-empty selected scope;
- source provenance labels;
- temporal span;
- state breadth;
- market breadth;
- observation volume;
- arrival-quantity availability;
- coordinate coverage;
- weather market coverage.

Hard academic-integrity failures produce `BLOCKED`. Coverage deficiencies produce `READY_WITH_WARNINGS` and must be discussed rather than silently filled or hidden. Thresholds are configurable because a one-state pilot and a national final analysis have different legitimate requirements.

Outputs:
- `outputs/empirical_readiness.json`
- `outputs/empirical_readiness.csv`

## 3. Freeze creation
Example:

```bash
python -m agriflow freeze-scope \
  --commodity Onion --commodity Tomato \
  --start 2019-01-01 --end 2025-12-31 \
  --label final-paper-v1
```

The command creates a new directory under `outputs/freezes/` containing, as available:
- `market_daily.csv` — exact filtered market panel;
- `markets.csv` — only markets represented in the frozen panel, retaining coordinate provenance;
- `weather_daily.csv` — only matching market/date weather rows;
- `readiness.json` — complete gate report and policy;
- `freeze_manifest.json` — scope, timestamp and per-file SHA-256 hashes;
- `SHA256SUMS.txt` — human/tool-verifiable integrity list;
- `provenance/` — available catalog/checkpoint/coordinate/boundary/source-register sidecars copied at freeze time and checksum-protected.

The freeze command refuses DEMO-only data by default. `--allow-demo-for-testing` exists only to test software behavior and must never be used to create report findings.

## 4. Integrity verification
Before analysis, presentation or report regeneration:

```bash
python -m agriflow verify-freeze outputs/freezes/<freeze-directory>
```

Any missing or modified frozen input causes verification to fail. If data correction is scientifically justified, create a **new freeze** rather than editing an old one.

## 5. Frozen-run analysis
Run:

```bash
python -m agriflow analyze-freeze outputs/freezes/<freeze-directory>
```

This creates a `results/` directory inside the freeze. In addition to the normal analytical tables, Phase 4 adds temporal robustness outputs:
- `lead_lag_yearly_<commodity>.csv`;
- `edge_stability_<commodity>.csv`;
- `leader_yearly_<commodity>.csv`;
- `leader_stability_<commodity>.csv`;
- `empirical_run_summary.json`;
- `RESULTS_SUMMARY.md`;
- `results_manifest.json`.

`RESULTS_SUMMARY.md` is a reproducibility aid, not automatically publishable prose. It intentionally uses non-causal language and must be reviewed against the underlying tables before inclusion in the paper.

## 6. Temporal robustness
A full-period lead-lag network can be dominated by one unusual subperiod. AgriFlow therefore re-estimates the network independently within each evaluable calendar year.

For each directed edge, the stability table reports:
- evaluable years;
- years in which the same direction passed all overlap/effect-size/FDR gates;
- persistence ratio;
- median correlation magnitude;
- median inferred lag;
- median aligned overlap.

For each potential leader, year-level source-oriented influence rankings are summarized with:
- years present;
- mean and median rank;
- mean and median influence score;
- number of years ranked in the top three.

A market should not be described as a persistent price leader merely because it ranks first in the pooled full-period network. The year-level evidence must be inspected.

## 7. Interpretation hierarchy
Permitted language depends on evidence strength.

### Descriptive
- "Market A had the highest median modal price in the selected window."
- "A market crunch candidate coincided with low arrivals and high price."

### Associational
- "Greater geographic distance was associated with lower daily-return co-movement."
- "Extreme rainfall episodes were followed by a median price response of X% in the observed event sample."

### Temporal leadership
- "Market A's daily price returns statistically preceded Market B's by two days under the configured lead-lag criteria."
- "Market A ranked as the most persistent upstream price-leadership node across N evaluable years."

### Not supported without a causal design
- "Market A controls onion prices in India."
- "Rainfall caused the price increase."
- "The network represents physical commodity transport routes."

## 8. Final-paper acceptance gate
Before any numeric result is inserted into the IEEE-style report:
- readiness status is not `BLOCKED`;
- `verify-freeze` passes;
- result manifest exists;
- result numbers are taken from the frozen `results/` directory, not an exploratory dashboard state;
- DEMO data are absent;
- limitations corresponding to every WARN gate are documented;
- temporal stability is reported for any market-leadership claim;
- QAP-style evidence accompanies geographic-distance significance claims;
- weather results remain explicitly observational/descriptive unless a separate causal design is implemented.
