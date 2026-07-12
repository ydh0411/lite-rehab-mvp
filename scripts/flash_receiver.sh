#!/usr/bin/env sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 /dev/cu.usbmodem-RECEIVER" >&2
  echo "If native USB does not reset, enter download mode with BOOT + RST." >&2
  exit 2
fi

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
. /Users/yuedonghan/.espressif/v6.0.2/esp-idf/export.sh >/dev/null 2>&1
idf.py -C "$ROOT/receiver" -p "$1" -b "${BAUD:-460800}" flash
