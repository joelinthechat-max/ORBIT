"""ORBIT portable desktop assistant."""
from pathlib import Path
import os
import sys

__version__ = "0.6.0"

# Optional, platform-specific wheels are vendored beside the source, never installed globally.
_ROOT = Path(__file__).resolve().parents[1]
_VENDOR = _ROOT / "VENDOR" / ("WINDOWS" if os.name == "nt" else "LINUX")
if _VENDOR.is_dir() and str(_VENDOR) not in sys.path:
    sys.path.insert(0, str(_VENDOR))
if os.name == "nt" and _VENDOR.is_dir():
    # ``PYTHONPATH`` directories do not process site .pth files. Reproduce only
    # pywin32's required local paths/DLL lookup, without executing its .pth code.
    for _sub in ("win32", "win32/lib", "pythonwin", "win32com"):
        _path = str(_VENDOR / _sub)
        if (_VENDOR / _sub).is_dir() and _path not in sys.path:
            sys.path.insert(0, _path)
    _DLL_DIR_HANDLES = []
    try:
        _DLL_DIR_HANDLES.append(os.add_dll_directory(str(_VENDOR / "pywin32_system32")))
        _DLL_DIR_HANDLES.append(os.add_dll_directory(str(_VENDOR)))
    except (AttributeError, OSError):
        pass
