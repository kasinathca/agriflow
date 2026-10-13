# AgriFlow final-review evidence status

Generated for software release **v1.4.3** on 2026-10-13.

This folder contains only evidence generated from the locally ingested REAL CEDA/AGMARKNET
Onion observations. Synthetic fixtures are excluded from every result table and figure.
The current scope contains 7,794 processed market-day observations across 25 markets and
four Maharashtra districts, covering 2023-01-01 through 2025-10-30.

The supplied CSI3004 course-project PDF was reviewed. The final deck follows its required
problem, objectives, proposed solution, dataset, methodology, implementation, results,
application, challenges, conclusion and references coverage in 15 slides.

## Current evidence and limits

- `01_dataset/` contains dataset, state, market, date and missingness evidence.
- `02_preprocessing/` records the raw-to-market-day quality changes.
- `04_results/` contains current descriptive/statistical REAL result tables.
- `05_figures/` contains REAL-data interactive figures only.
- `06_dashboard_screenshots/` shows the dashboard's REAL mode.
- `07_evaluation/` contains coverage, scope-selection and readiness gates.
- `manifest/final_review_manifest.json` records machine-readable scope and limitations.
- `forecasting/` contains the six-model experiment, ten held-out metrics, saved predictions,
  next-report forecasts, model artifact, methodology and interactive figures.
- `AgriFlow_Final_Review.pptx` is the generated academic review deck.

Readiness is `READY_WITH_WARNINGS`, not paper-final. State breadth is one, coordinate and
weather coverage are zero, the full Maharashtra download was blocked by sustained CEDA
latency/rate limiting, and no final empirical freeze has passed. Current lead-lag and crunch
tables are exploratory associations, not causal findings. The forecasting experiment is also
historical: the data ends on 2025-10-30 and does not represent a current October 2026 quotation.
