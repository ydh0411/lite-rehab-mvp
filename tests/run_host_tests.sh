#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
BUILD="$ROOT/tests/build"
mkdir -p "$BUILD"

cc -std=c17 -Wall -Wextra -Werror -I"$ROOT/shared" \
  "$ROOT/tests/test_motion_packet.c" "$ROOT/shared/motion_packet.c" \
  -o "$BUILD/test_motion_packet"

cc -std=c17 -Wall -Wextra -Werror -I"$ROOT/shared" \
  "$ROOT/tests/test_motion_logic.c" "$ROOT/shared/motion_logic.c" -lm \
  -o "$BUILD/test_motion_logic"

cc -std=c17 -Wall -Wextra -Werror -I"$ROOT/shared" \
  "$ROOT/tests/test_feedback_logic.c" "$ROOT/shared/feedback_logic.c" \
  -o "$BUILD/test_feedback_logic"

cc -std=c17 -Wall -Wextra -Werror -I"$ROOT/shared" \
  "$ROOT/tests/test_ecg_logic.c" "$ROOT/shared/ecg_logic.c" -lm \
  -o "$BUILD/test_ecg_logic"

"$BUILD/test_motion_packet"
"$BUILD/test_motion_logic"
"$BUILD/test_feedback_logic"
"$BUILD/test_ecg_logic"
