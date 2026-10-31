#!/bin/sh
set -eu
ORBIT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PYTHON_HOME="$ORBIT_ROOT/RUNTIME/LINUX/python"
PYTHON="$PYTHON_HOME/bin/python3.12"
if [ ! -x "$PYTHON" ]; then
  printf '%s\n' "ORBIT portable Linux runtime not found: $PYTHON" "Extract the complete archive and select the Linux x86_64 runtime."
  exit 2
fi
export PYTHONHOME="$PYTHON_HOME"
export PYTHONPATH="$ORBIT_ROOT"
export PYTHONNOUSERSITE=1
export PYTHONUTF8=1
export PLAYWRIGHT_BROWSERS_PATH="$ORBIT_ROOT/RUNTIME/LINUX/browser-cache"
export PLAYWRIGHT_SKIP_BROWSER_GC=1
cd "$ORBIT_ROOT"
exec "$PYTHON" -m orbit.app
