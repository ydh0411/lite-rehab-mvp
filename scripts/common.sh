#!/usr/bin/env sh

literehab_python()
{
  if [ -n "${PYTHON:-}" ]; then
    printf '%s\n' "$PYTHON"
    return 0
  fi
  if [ -n "${VIRTUAL_ENV:-}" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
    printf '%s\n' "$VIRTUAL_ENV/bin/python"
    return 0
  fi
  if [ -n "${CONDA_PREFIX:-}" ] && [ -x "$CONDA_PREFIX/bin/python" ]; then
    printf '%s\n' "$CONDA_PREFIX/bin/python"
    return 0
  fi
  for candidate in python3.12 python python3
  do
    if command -v "$candidate" >/dev/null 2>&1; then
      command -v "$candidate"
      return 0
    fi
  done
  echo "Python was not found. Activate the LiteRehab environment or set PYTHON." >&2
  return 1
}

literehab_load_esp_idf()
{
  if command -v idf.py >/dev/null 2>&1; then
    return 0
  fi

  if [ -n "${IDF_EXPORT:-}" ] && [ -f "$IDF_EXPORT" ]; then
    . "$IDF_EXPORT" >/dev/null 2>&1
    return 0
  fi
  if [ -n "${IDF_PATH:-}" ] && [ -f "$IDF_PATH/export.sh" ]; then
    . "$IDF_PATH/export.sh" >/dev/null 2>&1
    return 0
  fi

  for candidate in \
    "$HOME/esp/esp-idf/export.sh" \
    "$HOME"/.espressif/*/esp-idf/export.sh
  do
    if [ -f "$candidate" ]; then
      . "$candidate" >/dev/null 2>&1
      return 0
    fi
  done

  echo "ESP-IDF was not found. Export IDF_PATH, set IDF_EXPORT, or source export.sh." >&2
  return 1
}
