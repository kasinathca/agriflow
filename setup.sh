#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PY=${PYTHON:-python3}
command -v "$PY" >/dev/null 2>&1 || { echo "Python 3.10+ is required."; exit 1; }
"$PY" - <<'PY'
import sys
if sys.version_info < (3,10):
    raise SystemExit('Python 3.10+ is required')
PY
if [ ! -d .venv ]; then "$PY" -m venv .venv; fi
. .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python -m pip install -e . --no-deps
[ -f .env ] || cp .env.example .env
python -m agriflow init
python -m agriflow analyze
python -m pytest -q
printf '\nAgriFlow setup complete. Run ./run.sh\n'
