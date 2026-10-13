# AgriFlow Final Verification Report

Generated: 2026-10-13  
Repository starting commit: `1369b6e7cd17df5345bd42cefe4c05e278aa0894` (`main`)  
Verification status: **PASS with documented limitations**

## Executed evidence

- Data: 7,794 processed REAL CEDA/AGMARKNET Onion market-day rows, 25 markets, 4 Maharashtra districts, 2023-01-01 through 2025-10-30; SHA-256 `a4bea38608bdc5d525bc7d0e8d30d34f1f67a5132dc09004ba9c126837c0a82e`.
- Modeling cohort: 7,378 complete rows across 23 eligible markets after excluding 322 incomplete-lag rows and 2 markets with fewer than 120 observations.
- Temporal split: 5,199 train rows through 2025-01-13; 1,106 validation rows through 2025-06-07; 1,073 test rows from 2025-06-08 through 2025-10-30.
- Selection: M0 Persistence by lowest validation MAE (128.177 INR/q); validation RMSE tie-break was not required.
- Held-out result: MAE 101.398 INR/q, RMSE 180.973 INR/q, 0.0% improvement versus persistence because persistence itself won.
- Automated tests: 71 passed, 0 failed, 0 skipped using `.venv\Scripts\python.exe -m pytest -q --basetemp .pytest-tmp`.
- Targeted quality check: Ruff passed for the forecasting extension and touched integration files with legacy broad-exception rules ignored. The whole pre-existing repository still has unrelated Ruff debt.
- CLI smoke: prediction succeeded for `maharashtra__ahmadnagar__akole` using saved artifacts.
- Dashboard smoke: live Forecasting tab loaded saved REAL artifacts, market forecast, held-out metric, actual-versus-predicted chart and comparison table; no training occurred in callbacks.
- Presentation: 15 slides, 6 native charts, 5 native tables and 1 verified dashboard image. Package integrity, native-object, font, re-import and layout validation passed with 0 findings.
- PDF: 15 pages exported by PowerPoint; every rendered page was visually inspected with no clipping, overlap or unreadable content found.

## Acceptance criteria traceability

| ID | Status | Evidence |
|---|---|---|
| AC-01 | PASS | Full 71-test suite passed; existing analysis tabs remain in `src/agriflow/ui/app.py`. |
| AC-02 | PASS | Normal training, prediction and dashboard paths use local files; `.env.example` marks credentials acquisition-only. |
| AC-03 | PASS | `forecasting/dataset_manifest.json` records source, tier, mode, scope and input checksum. |
| AC-04 | PASS | Target is `modal_price` in INR/q; horizon is the next reported market observation. |
| AC-05 | PASS | Market-grouped lags and one-observation-shifted rolling features are tested in `tests/test_forecasting.py`. |
| AC-06 | PASS | M0 Persistence, M1 Lag-7, Ridge, Decision Tree, Random Forest and Hist Gradient Boosting executed. |
| AC-07 | PASS | MAE, MSE, RMSE, R-squared, MAPE, sMAPE, WAPE, Median AE, MBE and directional accuracy saved. |
| AC-08 | PASS | All six test rows in `model_comparison.csv` use the same 1,073-row held-out cohort. |
| AC-09 | PASS | Lowest validation MAE selects the model; validation RMSE resolves ties. Test data is comparison-only. |
| AC-10 | PASS | `forecasting/model_comparison.csv` contains measured validation and test values from the executed run. |
| AC-11 | PASS | Limitations are recorded in the methodology document, final-review README and slides 8, 13 and 14. |
| AC-12 | PASS | Four genuine Plotly HTML plots were generated from saved predictions and metrics. |
| AC-13 | PASS | `python -m agriflow predict --market-id ...` returned a saved next-report forecast. |
| AC-14 | PASS | Browser smoke verified the Forecasting dashboard tab and its saved-artifact views. |
| AC-15 | PASS | Overview, India Map, Market Influence, Weather and Crunch, Geography, Data Quality, Research Status, and Methods views remain available. |
| AC-16 | PASS | `AgriFlow_Final_Review.pptx` contains exactly 15 slides; PDF export also exists. |
| AC-17 | PASS | Slides 5–9 cover data, preprocessing, methodology, six models and ten metrics. |
| AC-18 | PASS | Slides 10–11 use saved measured comparison and held-out prediction results. |
| AC-19 | PASS | Slide 12 shows application evidence; slide 13 documents challenges and drawbacks. |
| AC-20 | PASS | Tests, project validator, CLI smoke, browser smoke, PPTX validator and PDF render review executed. |
| AC-21 | PASS | `scripts/validate_final_presentation.py` reconciled deck claims against saved JSON/CSV and returned 0 findings. |
| AC-22 | PASS | README and final-review README provide Windows first-run and repeat-run commands. |

## Known limitations

- Experimental coverage is Onion in 25 markets across four Maharashtra districts, not all India.
- Reports are irregular, so the horizon is next reported observation rather than an exact calendar day.
- The validation-selected result is a persistence baseline. The tested ML candidates did not improve validation MAE; no ML advantage is claimed.
- Ridge achieved a lower held-out RMSE and higher R-squared than persistence, but it was not selected because the declared validation-MAE rule was fixed before test comparison.
- The first forecast is price-only. Arrivals have uncertain units and verified weather coverage is unavailable.
- Data ends on 2025-10-30; forecasts are historical/offline, not live market quotes.
