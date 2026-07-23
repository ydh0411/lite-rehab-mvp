#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
. "$ROOT/scripts/common.sh"
literehab_load_esp_idf

idf.py -C "$ROOT/wearable" build
idf.py -C "$ROOT/receiver" build
