#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_DIR="$ROOT/web"
PYTHON_BIN="${PYTHON:-python}"
CAMERA_SOURCE="auto"

if [[ $# -gt 0 && "$1" != --* ]]; then
  CAMERA_SOURCE="$1"
  shift
fi

if [[ ! -d "$WEB_DIR/node_modules" ]]; then
  (cd "$WEB_DIR" && npm ci)
fi

if [[ ! -f "$WEB_DIR/dist/index.html" ]] || \
   find "$WEB_DIR/src" -type f -newer "$WEB_DIR/dist/index.html" -print -quit | grep -q .; then
  (cd "$WEB_DIR" && npm run build)
fi

export PYTHONPATH="$ROOT/python${PYTHONPATH:+:$PYTHONPATH}"
exec "$PYTHON_BIN" "$ROOT/python/run_web_dashboard.py" \
  --camera-source "$CAMERA_SOURCE" \
  "$@"
