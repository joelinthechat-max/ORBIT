#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PY="$ROOT/RUNTIME/LINUX/python/bin/python3.12"
[ -x "$PY" ] || { echo "Bundled Linux Python missing: $PY" >&2; exit 2; }
export PYTHONHOME="$ROOT/RUNTIME/LINUX/python"
export PYTHONPATH="$ROOT:$ROOT/VENDOR/LINUX"
export PYTHONNOUSERSITE=1
export PLAYWRIGHT_BROWSERS_PATH="$ROOT/RUNTIME/LINUX/browser-cache"
export PLAYWRIGHT_SKIP_BROWSER_GC=1
echo "This downloads Playwright's pinned Chromium build into: $PLAYWRIGHT_BROWSERS_PATH"
echo "Host OS browser libraries may still be required. No administrator install is attempted."
"$PY" -m playwright install chromium
