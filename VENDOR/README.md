# ORBIT v0.5 vendored optional dependencies

The platform-matched Python packages are extracted/installed only into `VENDOR/LINUX/` or `VENDOR/WINDOWS/`; `orbit/__init__.py` adds only the current platform folder to the bundled interpreter. No host-global Python installation is modified.

- Both targets: Playwright Python 1.64.1, Pillow 12.3.0 and required Playwright support modules. These are optional in practice: the offline core still starts if browser launch is unavailable.
- Windows x64: PyAutoGUI 0.9.54, PyScreeze, PyGetWindow, MouseInfo, PyMsgBox, PyTweening, PyRect, Pyperclip and pywin32 312 are vendored to support the optional Windows desktop adapter. Windows execution is not available in this build environment; this import path and GUI behavior require clean-Windows verification.
- Linux x86_64: desktop screenshot uses bundled Pillow and the explicit X11 `xdotool` fallback when PyAutoGUI is absent. X11 tools and system libraries are still host-provided; Wayland policy is not bypassed.

The corresponding `.dist-info/licenses`, license and notice files from downloaded distributions are retained. Chromium/Playwright browser executables are **not** bundled. The optional `setup_browser_linux.sh` and `setup_browser_windows.bat` scripts download the browser build selected by Playwright into `RUNTIME/<platform>/browser-cache/` only when the user runs them. Internet is needed for this optional installation; no admin install is attempted. Browser binaries are platform-specific, large, have separate distribution terms and system-library requirements. Alternatively, configure an existing compatible Chromium/Edge executable. Keep browser automation disabled until you have reviewed the risks and availability.
