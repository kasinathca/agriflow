# AgriFlow v1.4.3 — CEDA Integration and National-Map Stabilization

Release date: 2026-10-13

## Fixed and validated
- Kept the India choropleth on a stable national frame while state selection continues to filter linked KPIs and trends.
- Normalized GeoJSON ring winding so Plotly renders state polygons rather than their geographic complements.
- Prevented REAL prices from silently loading DEMO market coordinates or weather.
- Added explicit unavailable states for REAL weather and coordinate-dependent network/geography views.
- Normalized mixed timezone representations during resumable panel merges.
- Preserved all-missing arrival groups without numerical runtime warnings.
- Reused validated CEDA catalog caches during resumable downloads to avoid redundant catalog traffic.
- Added an append-only CEDA ingestion provenance entry and current REAL readiness to the dashboard.

## REAL CEDA evidence
- Validated the live CEDA catalog: 453 commodities, 36 states/UTs and 640 district IDs.
- Verified a two-district Onion/Maharashtra pilot for 2023–2025 and checkpoint replay.
- Retained 10 successful district/year checkpoints after the full-state expansion encountered sustained CEDA latency/rate limiting.
- Current processed evidence contains 7,794 REAL market-day observations, 25 markets and four districts from 2023-01-01 through 2025-10-30.
- Arrival coverage is 82.10%; CEDA supplied no quantity unit field, so `arrival_unit=UNKNOWN` remains explicit.
- Readiness is `READY_WITH_WARNINGS`: state breadth, reviewed coordinates and weather coverage remain incomplete. No final empirical freeze is claimed.

---

# AgriFlow v1.4.2 — Dashboard and Runtime Stabilization

Release date: 2026-10-13

## Fixed
- Made India ADM1 property detection provider-independent and validated boundary-to-data matches before constructing a choropleth.
- Canonicalized both GeoJSON and mandi state names, including provider transliterations such as `Mahārāshtra`, so all matching states render and remain clickable.
- Replaced the silent empty-map failure with a coordinate fallback or an explicit unavailable-state message.
- Changed real-data imports and CEDA rebuilds to merge compatible market-day panels instead of blindly overwriting prior authoritative data.
- Prevented repeated identical market-day arrival totals from being summed across variety rows and blocked aggregation across mixed arrival units.

## Runtime and verification
- Added `start_agriflow.bat` as the one-click Windows setup/launch path.
- Added focused choropleth, canonicalization, fallback, arrival and panel-merge regression tests.
- DEMO/REAL provenance gates, non-causal interpretation language and empirical freeze protections remain unchanged.

## Remaining empirical dependency
- No CEDA or data.gov.in credential is present locally. The official OGD manual download also requires user details and CAPTCHA, so no REAL dataset or final empirical freeze is claimed in this release.
- The course-project PDF referenced by the completion brief was not supplied in the workspace or attachment set; PDF-specific evidence mapping remains pending that file.

---

# AgriFlow v1.4.0 — Provenance-Gated Real-Data Bootstrap

Release date: 2026-10-07

This release hardens the transition from verified software to academically defensible real-data analysis. The central objective is to ensure that authentic-looking but secondary, user-supplied or mirrored data can never silently become final-paper evidence.

# AgriFlow v1.4.1 — CI Compatibility Fix

Release date: 2026-10-07

## Fixed
- Fixed Python 3.10 and Python 3.11 parsing failure in the POWER weather planning CLI output.
- Refactored POWER cell-count reporting for cross-version compatibility.
- GitHub Actions now installs the declared development dependency set through `.[dev]`.
- CI now explicitly performs Python compilation and structural validation before running tests.
- Disabled matrix fail-fast so Python 3.10, 3.11 and 3.12 are independently validated.

## Scope
This is a maintenance release. No analytical methodology, dataset provenance policy, or empirical interpretation has changed.

## Added / changed
- record-level `source_tier` classification with conservative inference;
- paper-acceptable tiers restricted to `PRIMARY_OFFICIAL` and `CURATED_OFFICIAL_DERIVED`;
- final empirical readiness now contains a hard `paper_acceptable_source_tier` gate;
- dedicated `import-data-gov-csv` route for manually downloaded official Government OGD / AGMARKNET exports;
- dedicated `import-ceda-csv` route for manually downloaded CEDA Agri-Market exports;
- generic `import-prices` is restricted to `USER_SUPPLIED` or `SECONDARY_MIRROR` and cannot self-promote to an authoritative tier;
- source-tier metadata survives normalization and daily aggregation;
- append-only `data/raw/ingest_provenance.jsonl` records source, tier, row count, retained raw file and SHA-256 hash;
- the ingest provenance ledger is included in empirical freeze provenance bundles when present;
- `agriflow doctor` provides an offline credential/data/readiness diagnostic without revealing secrets;
- run manifests and quality summaries expose observed source tiers;
- Phase 5 protocol, ADR, functional/non-functional requirements, risks, test-plan and traceability updates.

## Credential-free academic workflow
A user who does not yet have API credentials can manually download an official export and preserve its provenance:

```bash
python -m agriflow import-data-gov-csv path/to/official_ogd.csv
python -m agriflow import-ceda-csv path/to/ceda_export.csv --state Maharashtra --commodity Onion
python -m agriflow doctor
```

A third-party mirror remains useful for exploratory engineering, but must be imported through the generic route and is automatically blocked from final-paper freezes.

## Verification
- 41 automated tests pass after Phase 5 additions.
- New tests verify conservative tier inference, portal-column normalization, tier preservation, final-paper blocking of user/secondary data, rejection of official self-promotion through the generic CLI, and separation of official import commands.
- Python compilation, structural validation, DEMO initialization, offline doctor diagnostics and exploratory analysis remain regression-tested.
- Final clean-release verification is recorded in `docs/15_BUILD_VERIFICATION.md`.

## Remaining empirical dependency
No user CEDA or Government OGD API credential is embedded in this repository, and no unsupported secondary mirror is promoted to final evidence. Multi-year India-wide empirical claims still require authoritative real data, reviewed coordinates and weather coverage to pass the readiness/freeze gates.

---

# AgriFlow v1.3.0 — Empirical Freeze & Temporal-Robustness Baseline

Release date: 2026-10-06

This release turns the v1.2 spatial/weather system into a reproducible paper-grade workflow. The primary design objective is to prevent mutable exploratory dashboard state, DEMO data or one unstable time period from becoming an unsupported academic claim.

## Added / changed
- explicit empirical-readiness audit for selected commodity/date scope;
- hard REAL-only and source-provenance gates before a final empirical freeze;
- configurable temporal, state, market, observation, arrivals, coordinate and weather-coverage gates;
- named `outputs/freezes/<timestamp>_<label>/` snapshots containing the exact market, coordinate and weather rows used;
- SHA-256 integrity manifests and `verify-freeze` tamper detection;
- freeze-local paper analysis with separate result manifest;
- independent calendar-year lead-lag network re-estimation;
- directed-edge persistence ratios across evaluable years;
- year-level source-oriented influence ranks and leader-stability summaries;
- machine-generated `RESULTS_SUMMARY.md` that deliberately avoids causal wording;
- dashboard **Research Status** tab exposing the latest freeze/readiness state;
- Phase 4 protocol, ADR, requirements, risks, test plan and traceability additions.

## New CLI workflow
```bash
python -m agriflow readiness-audit --commodity Onion --start 2019-01-01 --end 2025-12-31
python -m agriflow freeze-scope --commodity Onion --start 2019-01-01 --end 2025-12-31 --label paper-v1
python -m agriflow verify-freeze outputs/freezes/<freeze-directory>
python -m agriflow analyze-freeze outputs/freezes/<freeze-directory>
```

`freeze-scope` refuses DEMO-only data unless `--allow-demo-for-testing` is deliberately supplied. Such testing freezes remain non-empirical and must never be cited as findings.

## Verification
- 35/35 automated tests pass after Phase 4 additions.
- New tests verify REAL readiness, DEMO blocking, successful freeze verification, tamper detection and recovery of a persistent constructed two-day leader→follower relationship in two independent years.
- Full exploratory demo analysis remains regression-tested.
- The clean candidate ZIP was extracted separately; initialization, 35 tests, structural validation, freeze verification and frozen-run analysis all passed from the packaged copy.
- Frozen-run workflow is smoke-tested on a DEMO snapshot only for software verification; those numbers are not empirical findings.

## Remaining empirical dependency
The build environment does not possess the user's CEDA credential or the final reviewed pan-India coordinate dataset. Therefore v1.3 provides and verifies the complete reproducible empirical workflow, but it does **not** fabricate final India-wide findings. Those must be generated on the target machine from the user's REAL data freeze.
