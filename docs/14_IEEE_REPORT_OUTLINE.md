# Planned IEEE-Style Report Structure

1. Abstract
2. Keywords
3. Introduction and motivation
4. Related work
5. Data sources and data-quality audit
6. System architecture
7. Methodology
   - preprocessing and comparability rules
   - price dispersion
   - supply-price association
   - lead-lag network inference
   - influence and integration measures
   - geographic-distance analysis
   - weather anomaly/event analysis
8. Experimental design and validation
9. Results
10. Dashboard / visual analytics system
11. Discussion
12. Threats to validity and limitations
13. Conclusion and future work
14. References

All final numerical results must be regenerated from the REAL data pipeline; demo fixture results must not appear as empirical findings.

## Phase 4 reporting requirements
For every numerical table/figure used in Sections 8–11, record the frozen-run directory name and verify its checksum manifest. Market-leadership results should report both pooled-period influence and calendar-year stability/persistence. Geographic-distance claims should report the QAP-style permutation statistic. Weather-event results should report event counts and remain explicitly observational unless a separate causal identification strategy is added.
