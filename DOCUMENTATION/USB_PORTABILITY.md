# ORBIT v0.5 USB Portability Report

## Package paths and launcher behavior

The extracted project directory is the installation. `run_windows.bat` derives its root from `%~dp0` and invokes `RUNTIME\WINDOWS\python\python.exe`; `run_linux.sh` derives its root from its own path and invokes `RUNTIME/LINUX/python/bin/python3.12`. Both set USB-local Python/home/module/cache paths and run the app from the project root; no host Python/pip or admin installation is required for the core. Source, config, SQLite, workspace, logs, screenshots, backups, optional browser profile/cache and model paths are project-relative.

The bundle includes standalone CPython 3.12.15 for Windows x86_64 MSVC and Linux x86_64 GNU, plus platform-local optional Python dependencies in `VENDOR/`. The user-triggered Playwright setup downloads a matching browser into the USB runtime tree; Chromium/Edge binaries are not included. Desktop host dependencies differ by OS: the Linux X11 path requires the interactive X server and system `xdotool`; Wayland may deny control. Windows packages are staged but untested on a Windows machine. License and dependency details are in `PORTABILITY_RESEARCH.md`, `V0.5_TECHNICAL_RESEARCH.md` and `VENDOR/README.md`.

## Results from this environment

The bundled Linux launcher was used for a real localhost HTTP acceptance workflow with Playwright/Chromium and the sandbox X11 display. The adapter captured a real screenshot, identified visible/active window metadata and safely moved/restored the cursor; no click or typing was sent to an application. Browser testing used only a disposable `127.0.0.1` fixture and covered page reading, non-password fill, password denial, observable click, safe JavaScript dialog dismissal, screenshot, tab switch and explicit form confirmation. The HTTP flow ran a bounded three-step model-free workspace task, verified the file, proved disabled desktop input/freshness/emergency-stop gates and cleaned its disposable state. A fake loopback API server confirmed managed process start/alias detection/stop; it used no model and performed no inference. Automated tests and syntax checks were recorded in `TEST_REPORT.md`.

This is an Ubuntu sandbox using local storage, system loader/libraries and host X11 tools/browser. It is not a physical USB test or target-device benchmark.

## Not verified and known limits

No clean Windows host/VM was available. Windows batch quoting, bundled runtime execution, vendor import/DLL initialization, PyAutoGUI screenshot/input, shortcuts, Playwright browser launch, persistence and Defender/SmartScreen remain untested. Linux ARM, Windows ARM, macOS, Linux musl and untested glibc ranges are not covered. No 4 GB physical/constrained device, target CPU, actual removable-volume detach, real user documents, real editor task, outside-web research or genuine local model inference was available.

A physical eject/power loss can still interrupt an OS/SQLite write. The app checks writable space and performs bounded preflights, but it cannot continue with the USB detached. Stop ORBIT and wait for active requests before safely ejecting.

## Suggested clean-host checklist

On a disposable Windows x64 system without Python, run `run_windows.bat`, verify the active interpreter path and confirm config/database/log/workspace remain under the extracted USB folder; then test Playwright setup and real desktop capture only in a clean throwaway account. Repeat on a supported Linux x86_64 GNU desktop with X11; separately note any Wayland denials. Record OS build, glibc, USB filesystem, path, free space, RSS/available RAM, browser and runtime process locations. Test restart recovery and emergency stop only with disposable files. Do not disable security controls to bypass an OS warning and do not unplug during an active request.
