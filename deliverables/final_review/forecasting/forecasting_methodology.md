# AgriFlow forecasting methodology

## Task

Predict the Onion modal wholesale price at the next reported market observation. The irregular observation sequence means this is not a next-day forecast.

## Data and cohort

- Source: CEDA_AGMARKNET (CURATED_OFFICIAL_DERIVED).
- Unit: INR per quintal.
- Eligible markets: 23 using at least 120 observations per market.
- Modeling rows after lag construction: 7,378.
- Split boundaries: train through 2025-01-13; validation through 2025-06-07; later observations form the test set.

## Features and leakage control

Lags 1, 2, 3, 7 and 14; prior-observation rolling means over 3, 7 and 14 reports; prior 7-report standard deviation; previous absolute and percentage change; market identity. Every rolling statistic starts from a one-observation shift.

## Models and selection

The experiment compares persistence, lag-7, Ridge, Decision Tree, Random Forest and Histogram Gradient Boosting on the same partitions. Validation MAE selects the model, with validation RMSE as tie-break. The held-out test set does not influence selection.

Selected model: **M0 Persistence**.

## Held-out results

| model | validation_mae | mae | rmse | r2 | directional_accuracy_pct |
| --- | --- | --- | --- | --- | --- |
| M0 Persistence | 128.177 | 101.398 | 180.973 | 0.543 | 29.543 |
| M1 Lag-7 | 310.512 | 172.801 | 242.203 | 0.181 | 46.132 |
| M2 Ridge | 151.793 | 112.479 | 165.843 | 0.616 | 42.311 |
| M3 Decision Tree | 163.945 | 111.801 | 182.323 | 0.536 | 38.583 |
| M4 Random Forest | 155.869 | 108.144 | 174.141 | 0.577 | 40.913 |
| M5 Hist Gradient Boosting | 149.407 | 108.734 | 171.299 | 0.590 | 41.193 |

## Limitations

The experiment covers Onion markets in four Maharashtra districts and ends in October 2025. It uses reported price history only, so it does not model weather, arrivals, policy changes or transport costs. Results measure historical next-report accuracy and do not represent current quotations.