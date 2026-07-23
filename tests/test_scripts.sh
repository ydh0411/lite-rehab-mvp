#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

for script in \
  "$ROOT/scripts/common.sh" \
  "$ROOT/scripts/build_all.sh" \
  "$ROOT/scripts/flash_wearable.sh" \
  "$ROOT/scripts/flash_receiver.sh" \
  "$ROOT/scripts/demo_doctor.sh" \
  "$ROOT/scripts/start_maixcam2_demo.sh" \
  "$ROOT/scripts/test_all.sh"
do
  sh -n "$script"
  if grep -E '/Users/[^/]+|/home/[^/]+' "$script" >/dev/null; then
    echo "Personal absolute path found in $script" >&2
    exit 1
  fi
done

TEMP_ROOT=$(mktemp -d)
trap 'rm -rf "$TEMP_ROOT"' EXIT HUP INT TERM

FAKE_PYTHON="$TEMP_ROOT/python"
printf '#!/usr/bin/env sh\nexit 0\n' >"$FAKE_PYTHON"
chmod +x "$FAKE_PYTHON"

(
  PYTHON="$FAKE_PYTHON"
  . "$ROOT/scripts/common.sh"
  [ "$(literehab_python)" = "$FAKE_PYTHON" ]
)

FAKE_EXPORT="$TEMP_ROOT/export.sh"
printf 'IDF_TEST_MARKER=loaded\nexport IDF_TEST_MARKER\n' >"$FAKE_EXPORT"

(
  PATH="/usr/bin:/bin"
  IDF_EXPORT="$FAKE_EXPORT"
  . "$ROOT/scripts/common.sh"
  literehab_load_esp_idf
  [ "${IDF_TEST_MARKER:-}" = "loaded" ]
)

echo "test_scripts: PASS"
