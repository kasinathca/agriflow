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

- **Problem:** the credentialed CEDA service validated successfully, but the full Maharashtra
  expansion later stalled/rate-limited an unfinished historical job.
- **Why it matters:** completed checkpoints are legitimate evidence, but they are not complete
  statewide coverage.
- **Solution:** retain commodity/district/year checkpoints, reuse validated local catalogs,
  rebuild only from successful chunks and report coverage explicitly.
- **Remaining limitation:** resume the same CEDA command when service capacity permits.

## REAL auxiliary-data isolation

- **Problem:** REAL prices could independently fall back to DEMO markets/weather.
- **Why it matters:** synthetic coordinates or weather could silently contaminate empirical analysis.
- **Solution:** REAL mode now returns typed empty auxiliary frames and explicit unavailable views.
- **Remaining limitation:** coordinate and weather analysis waits for reviewed real coordinates.
