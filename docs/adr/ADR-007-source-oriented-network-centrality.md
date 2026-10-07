# ADR-007 — Source-oriented network centrality

## Status
Accepted.

## Decision
For a directed edge `leader → follower`, compute the PageRank contribution on the reversed graph and expose it as `source_pagerank`.

## Rationale
Ordinary PageRank rewards nodes receiving links. In a price-transmission graph that can elevate downstream followers while the application labels the metric as market leadership. Reversing the graph aligns the centrality direction with the research interpretation.

## Consequences
The composite influence score remains exploratory. All component scores and significant outbound-edge counts remain visible for auditability.
