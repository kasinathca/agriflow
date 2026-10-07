# ADR-005 — Coverage-driven commodity basket freeze

**Status:** Accepted

## Context
Choosing commodities in advance can bias the project toward convenient crops and undermine the pan-India claim.

## Decision
Ingest a broader candidate panel, then rank commodities using observed state coverage, market breadth, observation count, temporal span, reporting density and arrival availability. Threshold eligibility and score components remain visible. The final basket is selected only after this audit plus substantive relevance review.

## Consequences
- the basket is defensible and data-driven;
- some expected commodities may be excluded for poor reporting;
- the score is a screening device, not a universal measure of agricultural importance.
