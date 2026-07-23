#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON=${PYTHON:-/opt/anaconda3/bin/python3.13}

"$ROOT/tests/run_host_tests.sh"
PYTHONPATH="$ROOT/python" "$PYTHON" -m pytest -q "$ROOT/python/tests"
PYTHONPATH="$ROOT/python" "$PYTHON" -m py_compile \
  "$ROOT/python/run_dashboard.py" "$ROOT/python/collect_data.py" \
  "$ROOT/python/train_1d_cnn.py" "$ROOT/python/train_multimodal.py" \
  "$ROOT/python/prepare_public_imu.py" \
  "$ROOT/python/literehab/"*.py "$ROOT/scripts/probe_cameras.py" \
  "$ROOT/maixcam2/main.py"
PYTHONPATH="$ROOT/python" "$PYTHON" "$ROOT/python/run_dashboard.py" \
  --headless-smoke-test

(cd "$ROOT/ios/LiteRehabCore" && swift test)

if command -v xcodebuild >/dev/null 2>&1 && xcodebuild -version >/dev/null 2>&1; then
  if ! command -v xcodegen >/dev/null 2>&1; then
    echo "SKIP: iOS app tests require XcodeGen (brew install xcodegen)."
  else
    SIMULATOR_ID=$(xcrun simctl list devices available | sed -n '/iPhone/s/.*(\([0-9A-F-]\{36\}\)) (.*)/\1/p' | head -1 | tr -d '[:space:]')
    if [ -z "$SIMULATOR_ID" ]; then
      echo "SKIP: iOS app tests require an installed iPhone Simulator runtime."
    else
      (cd "$ROOT/ios" && xcodegen generate >/dev/null && \
        xcodebuild -quiet -project LiteRehab.xcodeproj -scheme LiteRehab \
          -destination "platform=iOS Simulator,id=$SIMULATOR_ID" test \
          CODE_SIGNING_ALLOWED=NO -skipMacroValidation)
    fi
  fi
else
  echo "SKIP: iOS app tests require full Xcode."
fi

"$ROOT/scripts/build_all.sh"
