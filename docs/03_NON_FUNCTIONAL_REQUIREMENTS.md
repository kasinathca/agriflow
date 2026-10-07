# Non-Functional Requirements

| ID | Category | Requirement |
|---|---|---|
| NFR-01 | Reproducibility | Same demo seed/configuration must produce identical analytical outputs. |
| NFR-02 | Integrity | Synthetic/demo observations must never be presented as empirical AGMARKNET results. |
| NFR-03 | Reliability | Connector failures must be handled with timeouts, retries/caching and informative errors. |
| NFR-04 | Performance | Demo dashboard should load in <10 s on a typical student laptop after cache creation; expensive network analysis is bounded by configurable top-N markets. |
| NFR-05 | Portability | Windows PowerShell/Batch and POSIX shell bootstrap/run scripts are supplied. |
| NFR-06 | Maintainability | Modular package structure; typed functions; docstrings; configuration separated from analytics. |
| NFR-07 | Testability | Core analytics are pure functions wherever possible and tested against known fixtures. |
| NFR-08 | Explainability | Every composite score exposes component metrics and definitions. |
| NFR-09 | Accessibility | Dashboard avoids color-only meaning; labels/tooltips/tables accompany visual encodings. |
| NFR-10 | Security | API keys live only in `.env`, excluded by `.gitignore`; no arbitrary code execution or uploads are executed. |
| NFR-11 | Provenance | Processed outputs carry source/mode/date metadata; raw files are retained when downloaded. |
| NFR-12 | Academic quality | Claims distinguish association, temporal precedence and causation; limitations are visible. |
| NFR-13 | Resumability | Long-running historical ingestion must restart without repeating completed network calls. |
| NFR-14 | Auditability | Empty, successful, cached and failed ingestion jobs must be distinguishable after execution. |
| NFR-15 | Scope defensibility | Commodity inclusion must be based on explicit observed coverage criteria plus documented substantive review. |



## Phase 3 non-functional extensions
- **NFR-P3-01 Reproducibility:** coordinate, boundary and weather source provenance SHALL be persisted.
- **NFR-P3-02 External-service ethics:** public geocoding SHALL obey provider rate/usage restrictions and SHALL NOT be the unattended national bulk-acquisition strategy.
- **NFR-P3-03 Resumability:** weather downloads SHALL survive interruption without repeating completed cell-year jobs.
- **NFR-P3-04 Statistical transparency:** dependent pairwise spatial inference SHALL expose permutation evidence, not only naïve pairwise p-values.
- **NFR-P3-05 Interpretation safety:** UI labels SHALL distinguish association/temporal leadership from causation/control.

## Phase 4 non-functional extensions
- **NFR-P4-01 Immutability discipline:** final-report evidence SHALL be generated from a new snapshot rather than mutable working data.
- **NFR-P4-02 Integrity:** frozen inputs SHALL be checksum-verifiable and tampering SHALL be detectable.
- **NFR-P4-03 Reproducibility:** scope, thresholds and analytical settings SHALL be machine-readable.
- **NFR-P4-04 Temporal robustness:** pooled network conclusions SHALL expose subperiod stability diagnostics.
- **NFR-P4-05 Claim safety:** auto-generated summaries SHALL avoid causal wording unsupported by the methodology.

## Phase 5 non-functional extensions
- **NFR-P5-01 Provenance authority:** REAL observations SHALL not be treated as paper-acceptable solely because they are non-synthetic.
- **NFR-P5-02 Tamper evidence:** retained manual-source files SHALL have SHA-256 recorded at import time.
- **NFR-P5-03 Least privilege:** generic import tooling SHALL not permit arbitrary promotion of a file into an official source tier.
- **NFR-P5-04 Credential safety:** diagnostic output SHALL report only whether credentials are configured, never credential values.
- **NFR-P5-05 Recoverability:** when a live API is unavailable, a retained official portal export SHALL remain a supported reproducible ingestion route.
