#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CAMERA_SOURCE="${1:-auto}"
PYTHON_BIN="${PYTHON:-python}"

export PYTHONPATH="$ROOT/python${PYTHONPATH:+:$PYTHONPATH}"
exec "$PYTHON_BIN" "$ROOT/python/run_web_dashboard.py" \
  --host 0.0.0.0 \
  --mobile \
  --no-browser \
  --camera-source "$CAMERA_SOURCE"
