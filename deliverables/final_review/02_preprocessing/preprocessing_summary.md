# Implemented preprocessing

- tolerant source-column mapping and date/numeric parsing;
- canonical state names and stable `state__district__market` identifiers;
- invalid min/modal/max ordering excluded from ordered-price comparisons;
- deterministic market-day aggregation with median prices across variety/grade rows;
- repeated identical market-day arrival totals counted once;
- arrival unit preserved where supplied, `UNKNOWN` where absent, and mixed units not summed;
- authority-aware append/deduplication that preserves prior compatible imports;
- source, source tier, retained raw file and SHA-256 provenance recording.

`missing report != zero`. Network price inference does not use arbitrary forward filling and
does not bridge non-consecutive reporting gaps.

For the current CEDA scope, 8,499 raw canonical rows become 7,794 unique market-day rows.
The processed panel has zero duplicate market-day keys and zero retained min/modal/max order
violations. The 1,395 missing arrival values remain missing; they are not converted to zero.
