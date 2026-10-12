# Dataset status

The active analytical panel is REAL historical Onion data obtained from the authenticated
CEDA Agri Market API, a curated route over AGMARKNET observations. It contains 8,499 raw
canonical rows from 10 completed district/year checkpoints and 7,794 unique market-day rows.
Coverage spans 25 markets in Ahmadnagar, Akola, Amravati and Aurangabad from 2023-01-01 to
2025-10-30.

All observations are labelled `source=CEDA_AGMARKNET`,
`source_tier=CURATED_OFFICIAL_DERIVED`, and `data_mode=REAL`. Arrival values are present for
82.10% of processed rows. The live quantity response exposes a `quantity` field but no unit
field, so `arrival_unit=UNKNOWN` is preserved for every row.

The full Maharashtra request did not finish because CEDA repeatedly stalled/rate-limited an
unfinished historical job. Statewide completeness is therefore not claimed. See the CSVs in
this directory for exact coverage and missingness.
