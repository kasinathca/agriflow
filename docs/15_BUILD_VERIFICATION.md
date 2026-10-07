# Build Verification Record — v1.4.0

Verification date: 2026-10-07

## Development-tree verification
- Python source/test compilation (`compileall`): **PASS**.
- Structural validation script: **PASS**.
- Automated unit/known-answer/integration tests: **41/41 PASS**.
- Deterministic DEMO initialization (`agriflow init --no-geojson`): **PASS**.
- Offline `agriflow doctor`: **PASS**; reports missing credentials without exposing secret values.
- End-to-end exploratory `agriflow analyze` on the deterministic DEMO fixture: **PASS**.
- Phase 5 source-tier processing and readiness regression tests: **PASS**.
- Generic import parser rejects `PRIMARY_OFFICIAL` self-promotion: **PASS**.
- Dedicated CEDA and Government OGD manual-import commands remain separate parser routes: **PASS**.
- Testing-only DEMO freeze with a synthetic ingest-provenance ledger: **PASS**.
- Freeze provenance bundle contains `provenance/ingest_provenance.jsonl`: **PASS**.
- SHA-256 verification of that testing-only freeze: **PASS**.

## Phase 5 known-answer / integrity checks
- `DATA_GOV_IN_AGMARKNET` conservatively maps to `PRIMARY_OFFICIAL`.
- `CEDA_AGMARKNET` conservatively maps to `CURATED_OFFICIAL_DERIVED`.
- Unknown/generic real-data imports do not silently become paper-authoritative.
- Source tier survives normalization and market-day aggregation.
- A REAL dataset classified `USER_SUPPLIED` fails the hard `paper_acceptable_source_tier` readiness gate.
- The generic `import-prices` CLI accepts only `USER_SUPPLIED` or `SECONDARY_MIRROR`.
- Official/curated manual imports have dedicated `import-data-gov-csv` and `import-ceda-csv` routes.
- Ingest provenance records include retained raw-file SHA-256 when a raw source file exists.
- The ingest-provenance ledger is copied into a paper freeze when present and is covered by the freeze checksum manifest.

## Source-authority policy verified in v1.4
Final-paper freezes accept only:
1. `PRIMARY_OFFICIAL` — e.g. Government of India OGD / AGMARKNET data; or
2. `CURATED_OFFICIAL_DERIVED` — e.g. CEDA Agri-Market data derived from AGMARKNET.

`SECONDARY_MIRROR`, `USER_SUPPLIED`, `UNKNOWN`, and `DEMO` are blocked from normal final-paper freezing. The `--allow-demo-for-testing` override remains strictly a software-verification escape hatch and does not convert DEMO data into empirical evidence.

## Empirical-source limitations of this build environment
1. No user CEDA Bearer credential is available in the artifact environment; therefore no live multi-year CEDA acquisition was attempted here.
2. No user Government OGD API key is available in the artifact environment; direct API acquisition was not attempted here.
3. No final reviewed pan-India mandi-coordinate file has been supplied; final coordinate quality must be reviewed on the target machine before spatial claims are frozen.
4. Secondary public mirrors were inspected only as engineering/bootstrap references and were **not** promoted to final evidence.
5. The build environment does not include the complete target-machine dependency stack required to launch the Dash HTTP application. Dashboard source is syntax-validated and underlying analytical/Plotly paths are covered by the established regression suite; `setup.bat` / `setup.sh` install runtime dependencies on the target machine.
6. DEMO outputs and testing-only freezes are software-verification artifacts and are prohibited from final empirical reporting.

## Target-machine Phase 5 acceptance sequence
1. Run `setup.bat` or `./setup.sh`.
2. Run `python -m agriflow doctor`.
3. Configure `CEDA_API_KEY` / `DATA_GOV_API_KEY`, **or** manually download an official CEDA/OGD export and use the dedicated importer.
4. Run a small real-data ingestion/import pilot and re-run `doctor`.
5. Expand candidate coverage and run `scope-audit`.
6. Import/review market coordinates.
7. Fetch/resume POWER weather.
8. Run `readiness-audit` on the intended paper scope.
9. Resolve every hard readiness failure, especially `paper_acceptable_source_tier`.
10. Create `freeze-scope` without the DEMO testing override.
11. Run `verify-freeze`.
12. Run `analyze-freeze` and use only freeze-local results in the final paper.

See `docs/22_PHASE5_SOURCE_PROVENANCE_AND_REAL_BOOTSTRAP.md` and ADR-010.

## Clean release-archive validation
The final v1.4 source-only ZIP is validated from a separate extraction after packaging. The final verification results are recorded below after that packaged-copy run.

### Candidate archive run
A source-only v1.4 candidate archive was extracted to a different directory and run without relying on the development working tree:
- archive extraction: **PASS**;
- Python compilation: **PASS**;
- automated tests: **41/41 PASS**;
- structural validation: **PASS**;
- `agriflow init --no-geojson`: **PASS**;
- offline `agriflow doctor`: **PASS**, correctly reports no credentials and DEMO fallback;
- end-to-end `agriflow analyze`: **PASS** in DEMO mode;
- imported package version: **1.4.0 PASS**.

The first combined candidate-validation shell invocation reached its execution timeout only after compilation, the 41-test suite, structural validation and initialization had already passed. The remaining `doctor`, analysis and version checks were rerun individually and passed; the timeout is therefore recorded as an orchestration timeout, not a project failure.

### Final archive run
The final v1.4 ZIP was independently extracted and validated again after the source manifest was regenerated:
- Python compilation: **PASS**;
- automated tests: **41/41 PASS**;
- structural validation: **PASS**;
- package version check (`1.4.0`): **PASS**;
- `PROJECT_MANIFEST.md`: **110/110 listed source-file hashes verified**;
- `agriflow init --no-geojson`: **PASS**;
- offline `agriflow doctor`: **PASS**;
- end-to-end DEMO `agriflow analyze`: **PASS**.

The archive SHA-256 is reported alongside the downloadable artifact because the ZIP hash necessarily changes if this verification record itself is updated.
