# Verification and Test Plan

## Automated unit tests
- schema normalization and price ordering
- daily market aggregation
- price-dispersion metrics
- supply-price correlation/elasticity
- lead-lag direction on a constructed known-lag time series
- FDR correction
- Haversine distance
- weather join and anomaly calculation
- crunch detection
- influence graph construction

## Integration tests
- demo fixture generation → preprocessing → analytics pipeline
- export generation
- connector parameter construction (HTTP calls mocked)
- CEDA Bearer/header contract, ID-list payloads and price/quantity merge
- resumable CEDA checkpoint/cache behavior
- coverage-driven commodity selection eligibility and ranking
- application module import and layout construction

## Manual acceptance tests
1. Fresh Windows machine: run `setup.bat`; then `run.bat`.
2. Fresh Linux/macOS shell: `./setup.sh`; then `./run.sh`.
3. Confirm demo badge appears without credentials.
4. Click a state on the map and confirm linked selector/charts update.
5. Change commodity and confirm all panels update consistently.
6. Select a leader and move ripple lag slider.
7. Disconnect network; cached/demo app continues to operate.
8. Add real API key; run `ceda-catalog`; confirm catalogs cache successfully.
9. Run a two-district CEDA pilot twice; second run must report cached jobs rather than repeat network calls.
10. Run `scope-audit`; verify component metrics and recommended flags are visible.

## Exit criteria
All automated tests pass; no uncaught exception in manual path; no synthetic data labelled REAL; data-source attribution shown; analytical edge creation obeys minimum overlap and significance thresholds.


## Phase 3 tests
- duplicate market display names in different states produce distinct IDs;
- market-return calculations preserve those distinct nodes;
- POWER cell quantization deduplicates nearby points;
- POWER cell-year checkpoints are reused on rerun and rebuild to multiple markets;
- QAP-style spatial permutation results are deterministic for a fixed seed and bounded;
- adjacent extreme weather days are declustered to one event episode;
- geoBoundaries fallback writes a provenance sidecar with licence metadata.

## Phase 4 tests
- REAL-mode readiness can pass under an explicit small pilot policy;
- DEMO data are blocked from empirical freezing by default;
- a valid freeze verifies successfully;
- modifying a frozen input is detected as a checksum mismatch;
- a constructed two-year, two-day leader→follower process is recovered in both evaluable years;
- temporal leader stability ranks the constructed upstream leader above the follower;
- frozen-run integration writes result/stability manifests even when arrival quantities have no variance;
- packaged-copy `freeze-scope --allow-demo-for-testing`, `verify-freeze`, and `analyze-freeze` complete without path errors.

## Phase 5 verification
- source-tier inference for Government OGD, CEDA, generic user files and DEMO fixtures;
- portal-style CSV heading normalization with explicit state/district/market/commodity metadata;
- source-tier persistence through daily aggregation;
- hard rejection of `USER_SUPPLIED`/`SECONDARY_MIRROR` rows by paper readiness;
- dedicated official importers retain raw-file SHA-256 provenance;
- `doctor` command reports credentials only as booleans and works fully offline.
