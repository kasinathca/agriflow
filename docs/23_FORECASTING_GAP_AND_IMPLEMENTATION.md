# Forecasting requirement gap and implementation record

Initial audit: 2026-10-13. Starting branch `main`; starting commit `1369b6e7cd17df5345bd42cefe4c05e278aa0894`; working tree clean.

| Requirement | Initial state | Action and validation |
|---|---|---|
| Existing market analysis | Complete | Preserve dashboard tabs and run regression tests. |
| Offline real dataset | Complete locally | Validate `data/processed/market_daily.csv` and record a checksum manifest. |
| Forecasting features | Missing | Add backward-looking market-group features and leakage tests. |
| Six models | Missing | Add two baselines and four scikit-learn regressors. |
| Temporal evaluation | Missing | Split by unique target date into approximately 70/15/15 partitions. |
| Ten metrics | Missing | Compute all metrics from validation and held-out predictions. |
| Forecast inference | Missing | Save a fitted model and next-report forecasts for eligible markets. |
| Dashboard forecast view | Missing | Add a read-only tab backed by saved artifacts. |
| PowerPoint | Missing | Generate and validate a 15-slide deck from saved evidence. |
| data.gov.in key dependency | Present only in optional fetch command | Deprecate direct fetching; training, dashboard and presentation use local historical data. |
| Testing | Existing suite present | Add forecast tests and rerun all tests with workspace-local pytest temp storage. |

The local dataset provides real CEDA/AGMARKNET Onion observations. It supports a defensible historical experiment but remains geographically limited to four Maharashtra districts and ends on 2025-10-30.
