#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
. "$ROOT/scripts/common.sh"
PYTHON_BIN=$(literehab_python)
SOURCE=${1:-auto}

PYTHONPATH="$ROOT/python" "$PYTHON_BIN" "$ROOT/python/run_dashboard.py" \
  --port auto \
  --camera-source "$SOURCE" \
  --side right \
  --output "$ROOT/python/sessions/maixcam2_demo.csv"
