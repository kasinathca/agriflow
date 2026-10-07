# Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---:|---:|---|
| Uneven mandi reporting | High | High | Coverage audit; minimum-density filters; visible limitations. |
| API downtime/rate limits | Medium | High | Cache, timeout/retry, local imports, deterministic demo mode. |
| CEDA/API authentication changes | Medium | Medium | Adapter isolation; CSV import path; config-based endpoints. |
| Missing market coordinates | High | Medium | Cached geocoding; district centroid fallback with quality flag; exclude low-quality pairs from distance analysis when required. |
| Spurious lead-lag edges | High | High | Returns not levels, minimum overlap, FDR correction, thresholds, caveat language. |
| Weather attribution overclaim | Medium | High | Event-study framing; no causal language; show confounders/limitations. |
| Huge all-India historical data | Medium | Medium | Chunked ingestion, commodity/date filters, top-N network cap, caching. |
| State boundary service unavailable | Low/Medium | Medium | Cache successful GeoJSON; fallback scatter/state selection. |
| Demo data mistaken for results | Low | High | Persistent DEMO label and provenance metadata. |


## Phase 3 risks
| Risk | Effect | Mitigation |
|---|---|---|
| Duplicate mandi names | silent cross-state merging | mandatory `market_id` composite identity |
| Inexact geocoding | distorted distance/weather assignment | coordinate quality flags; reviewed imports preferred |
| Public geocoder policy violation | service blocking / unethical use | explicit policy gate, request cap, throttling; no national unattended bulk path |
| Boundary service access changes | missing map polygons | source provenance + open geoBoundaries fallback |
| Pairwise pseudo-replication | overstated distance significance | QAP-style label permutation |
| Consecutive weather extremes counted repeatedly | inflated event sample | event declustering |
| Sink-oriented centrality mislabeled as leadership | incorrect leader ranking | PageRank on reversed graph plus exposed components |

## Phase 4 risks
| Risk | Effect | Mitigation |
|---|---|---|
| Exploratory data change after results are quoted | irreproducible paper figures/numbers | checksum-protected named empirical freeze |
| DEMO data copied into final paper | academic-integrity failure | hard REAL-mode freeze gate; persistent DEMO labeling |
| Pooled network hides regime/year instability | overstated price-leader conclusion | independent yearly re-estimation and persistence tables |
| Freeze corrected in place | silent evidence mutation | new-freeze policy; integrity verification before analysis |
| Missing weather/coordinates treated as complete | biased spatial/weather interpretation | explicit readiness coverage gates and visible WARN status |

## Phase 5 risks
| Risk | Effect | Mitigation |
|---|---|---|
| REAL secondary mirror mistaken for primary evidence | unsupported paper claims | mandatory source tiers + hard paper gate |
| User labels arbitrary CSV as official | provenance laundering | generic importer cannot assign official tiers |
| API unavailable close to submission | empirical run blocked | dedicated manual CEDA/OGD export importers with retained hashes |
| Manual export filter context lost | unreproducible scope | provenance note + required identity metadata + raw-file retention |
| Credential accidentally printed/logged | secret exposure | doctor reports boolean presence only; `.env` remains ignored by Git |
