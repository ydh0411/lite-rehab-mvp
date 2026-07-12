#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON=${PYTHON:-/opt/anaconda3/bin/python3.13}

"$ROOT/tests/run_host_tests.sh"
PYTHONPATH="$ROOT/python" "$PYTHON" -m pytest -q "$ROOT/python/tests"
PYTHONPATH="$ROOT/python" "$PYTHON" -m py_compile \
  "$ROOT/python/run_dashboard.py" "$ROOT/python/collect_data.py" \
  "$ROOT/python/train_1d_cnn.py" "$ROOT/python/train_multimodal.py" \
  "$ROOT/python/literehab/"*.py
PYTHONPATH="$ROOT/python" "$PYTHON" "$ROOT/python/run_dashboard.py" \
  --headless-smoke-test
"$ROOT/scripts/build_all.sh"
