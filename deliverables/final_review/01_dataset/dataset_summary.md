# Dataset status

No authoritative REAL dataset is available in this environment. The only active dataset is
the deterministic `AGRIFLOW_DEMO_SYNTHETIC` fixture covering five commodities, eight states
and sixteen markets from 2023-01-01 through 2025-12-31. It is suitable for software testing
only and is excluded from empirical findings, figures and screenshots.

To create legitimate dataset evidence, provide `CEDA_API_KEY` or `DATA_GOV_API_KEY` in the
ignored `.env`, or complete an official portal export and run the dedicated
`import-ceda-csv` / `import-data-gov-csv` command. Then run the readiness and freeze workflow
before generating review metrics.
