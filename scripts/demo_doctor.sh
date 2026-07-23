#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
. "$ROOT/scripts/common.sh"
PYTHON_BIN=$(literehab_python)
FAILURES=0
WARNINGS=0

pass()
{
  printf 'PASS  %s\n' "$1"
}

fail()
{
  printf 'FAIL  %s\n' "$1" >&2
  FAILURES=$((FAILURES + 1))
}

warn()
{
  printf 'WARN  %s\n' "$1"
  WARNINGS=$((WARNINGS + 1))
}

printf 'LiteRehab demo preflight\n'
printf 'Repository: %s\n' "$ROOT"
printf 'Python: %s\n\n' "$PYTHON_BIN"

if "$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if (3, 10) <= sys.version_info[:2] < (3, 13) else 1)'; then
  pass "Python version supports the full MediaPipe stack (3.10-3.12)"
else
  VERSION=$("$PYTHON_BIN" -c 'import platform; print(platform.python_version())')
  fail "Python $VERSION is unsupported for the full demo; use Python 3.10-3.12"
fi

for module in numpy cv2 serial torch fastapi uvicorn qrcode mediapipe
do
  if "$PYTHON_BIN" -c "import importlib.util; raise SystemExit(0 if importlib.util.find_spec('$module') else 1)"; then
    pass "Python module: $module"
  else
    fail "Missing Python module: $module"
  fi
done

if [ -f "$ROOT/python/models/imu_cnnbigru.pt" ]; then
  pass "IMU checkpoint"
else
  fail "Missing python/models/imu_cnnbigru.pt"
fi

if [ -f "$ROOT/python/models/pose_landmarker_lite.task" ]; then
  pass "MediaPipe pose task"
else
  fail "Missing python/models/pose_landmarker_lite.task"
fi

if [ -f "$ROOT/web/dist/index.html" ]; then
  pass "Web dashboard build"
else
  fail "Missing web/dist/index.html; run npm --prefix web ci && npm --prefix web run build"
fi

if find /dev -maxdepth 1 \( -name 'cu.usbmodem*' -o -name 'cu.usbserial*' -o -name 'ttyUSB*' -o -name 'ttyACM*' \) -print -quit 2>/dev/null | grep . >/dev/null; then
  pass "Serial device detected"
else
  warn "No USB serial device detected; connect the receiver before the hardware demo"
fi

if command -v npm >/dev/null 2>&1; then
  pass "npm"
else
  warn "npm is unavailable; it is only needed to rebuild the Web dashboard"
fi

if (literehab_load_esp_idf); then
  pass "ESP-IDF"
else
  warn "ESP-IDF is unavailable; dashboard use is unaffected, but firmware cannot be rebuilt"
fi

printf '\nPreflight summary: %s failure(s), %s warning(s)\n' "$FAILURES" "$WARNINGS"
[ "$FAILURES" -eq 0 ]
