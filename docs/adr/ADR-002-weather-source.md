# ADR-002 — NASA POWER for reproducible historical weather; IMD as reference

**Status:** Accepted

## Decision
Use NASA POWER daily agroclimatology data for automated historical weather integration. Keep IMD as the official Indian rainfall reference/current-data adapter.

## Rationale
A multi-year, programmatic historical pipeline must be reproducible on a student machine. IMD exposes current rainfall information and formal data-supply procedures for historical data; NASA POWER exposes a documented historical daily API. The distinction is disclosed in the UI and report.
