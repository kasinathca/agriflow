# ADR-001 — Dash/Plotly local web application

**Status:** Accepted

## Decision
Use Plotly Dash for the local web interface.

## Rationale
The project needs linked filters, click-driven state drill-down, network/ripple interactions and SVG-quality charts. Dash provides these interactions in Python, allowing the analysis code and presentation code to share tested data structures without a separate JavaScript application.
