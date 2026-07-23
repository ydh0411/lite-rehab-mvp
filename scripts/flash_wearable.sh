#!/usr/bin/env sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 /dev/cu.usbserial-WEARABLE" >&2
  exit 2
fi

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
. "$ROOT/scripts/common.sh"
literehab_load_esp_idf
idf.py -C "$ROOT/wearable" -p "$1" -b "${BAUD:-460800}" flash
