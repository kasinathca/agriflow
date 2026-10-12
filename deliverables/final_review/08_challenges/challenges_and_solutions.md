# Challenges and solutions

## State-name mismatches

- **Problem:** geoBoundaries uses transliterated names such as `Mahārāshtra`.
- **Why it matters:** valid polygons failed to match ordinary mandi state names.
- **Solution:** detect the provider property, strip combining marks, canonicalize both sides,
  validate matches and use an explicit fallback.
- **Remaining limitation:** a completely novel provider property falls back until added to the
  small supported candidate list.

## Import overwrite and arrival ambiguity

- **Problem:** import routes replaced the processed panel, and repeated market-day arrival
  totals could be counted once per variety row.
- **Why it matters:** prior authoritative observations could be lost and arrival totals inflated.
- **Solution:** authority-aware deterministic panel merging, repeated-total deduplication and
  mixed-unit blocking.
- **Remaining limitation:** providers that omit arrival units remain explicitly `UNKNOWN`.

## Authoritative empirical acquisition

- **Problem:** no API credential is configured; the official manual export requires personal
  fields and CAPTCHA.
- **Why it matters:** REAL dashboard and paper evidence cannot be generated honestly.
- **Solution:** preserve ready CEDA, OGD API and dedicated official CSV import routes.
- **Remaining limitation:** a human must supply a credential or complete the official export.
