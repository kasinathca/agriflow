# Contributing to AgriFlow

1. Create a feature branch.
2. Keep data-source logic inside `src/agriflow/data/sources/`.
3. Keep analytical functions independent of Dash where practical.
4. Add or update a test for every analytical change.
5. Run `pytest -q` and `python scripts/validate_project.py` before merging.
6. Record a new ADR when changing a frozen architecture/methodology decision.
7. Never commit `.env`, API keys, large raw datasets or generated output tables.
8. Never label synthetic/demo observations as empirical results.
