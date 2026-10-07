#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -d .venv ]; then echo "Run ./setup.sh first."; exit 1; fi
. .venv/bin/activate
python -m agriflow run
