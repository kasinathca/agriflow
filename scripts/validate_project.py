from __future__ import annotations
from pathlib import Path
import subprocess, sys

ROOT=Path(__file__).resolve().parents[1]
required=[
    "README.md","pyproject.toml","requirements.txt","setup.sh","setup.bat","run.sh","run.bat",
    "docs/01_SRS.md","docs/02_FUNCTIONAL_REQUIREMENTS.md","docs/03_NON_FUNCTIONAL_REQUIREMENTS.md",
    "docs/04_DATA_SPECIFICATION.md","docs/05_ANALYTICS_SPECIFICATION.md","docs/08_TEST_PLAN.md",
    "docs/18_PHASE2_EMPIRICAL_PROTOCOL.md","docs/19_CEDA_INGESTION_PROTOCOL.md","docs/20_PHASE3_SPATIAL_WEATHER_PROTOCOL.md","docs/21_PHASE4_EMPIRICAL_FREEZE_PROTOCOL.md",
    "src/agriflow/ui/app.py","src/agriflow/analytics/lead_lag.py","src/agriflow/analytics/selection.py",
    "src/agriflow/data/ceda_ingest.py","src/agriflow/data/weather_ingest.py","src/agriflow/data/identity.py","src/agriflow/research/freeze.py","src/agriflow/research/runner.py","src/agriflow/analytics/robustness.py",
    "tests/test_lead_lag.py","tests/test_ceda_ingest.py","tests/test_selection.py","tests/test_phase3_weather_ingest.py","tests/test_phase4_freeze.py","tests/test_phase4_robustness.py","tests/test_phase4_runner.py"
]
missing=[p for p in required if not (ROOT/p).exists()]
if missing:
    print("Missing required project files:",*missing,sep="\n - ")
    raise SystemExit(1)
print("Structural validation: PASS")
proc=subprocess.run([sys.executable,"-m","pytest","-q"],cwd=ROOT)
raise SystemExit(proc.returncode)
