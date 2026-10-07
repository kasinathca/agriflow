# Local Deployment Runbook

## Windows
1. Install Python 3.10+ and ensure `py` or `python` is on PATH.
2. Run `setup.bat` once.
3. Run `run.bat` for later launches.
4. Open `http://127.0.0.1:8050` if the browser does not open automatically.

## Linux/macOS
```bash
chmod +x setup.sh run.sh
./setup.sh
./run.sh
```

## Real data configuration
Copy `.env.example` to `.env` (the setup script does this automatically if absent). Add optional keys:
- `DATA_GOV_API_KEY=...`
- `CEDA_API_KEY=...`

Then run the ingestion CLI described in the README. Without keys, the app remains fully runnable in DEMO mode.


## Phase 3 real-data continuation
After the commodity basket is frozen: import/review market coordinates, dry-run POWER jobs, fetch weather with resumable checkpoints, rerun `analyze`, inspect distance/weather outputs, then launch the dashboard. Do not perform unattended national public-Nominatim geocoding.
