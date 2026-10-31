# Portable Python runtime selection and provenance

## Selected binaries

ORBIT v0.4 bundles Astral's `python-build-standalone` CPython 3.12.15 `install_only_stripped` builds for x86_64 Windows MSVC and x86_64 Linux GNU. Official release metadata is from tag `20261021`: https://github.com/astral-sh/python-build-standalone/releases/tag/20261021 and latest release JSON: https://raw.githubusercontent.com/astral-sh/python-build-standalone/latest-release/latest-release.json

- Windows archive: `cpython-3.12.15+20261021-x86_64-pc-windows-msvc-install_only_stripped.tar.gz`, source archive size 21,990,627 bytes; verified SHA-256 `aac5d331fc3307343f95928fdbea4583f0d53973d08c7e1d081884fbd229a0e1`.
- Linux archive: `cpython-3.12.15+20261021-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz`, source archive size 34,479,606 bytes; verified SHA-256 `6d7521138fd33afddc1ccd08abb007d9a2829e38117c2576f9efdc0ec73ce772`.

Both upstream release hashes were verified before extraction. The Windows runtime license is included at `RUNTIME/WINDOWS/python/LICENSE.txt`; the Linux license is `RUNTIME/LINUX/python/lib/python3.12/LICENSE.txt`. Auxiliary upstream `PYTHON.json` metadata was not present in the extracted install-only archives and is not claimed to be included. Refer to upstream release metadata and licensing documentation for the distribution build and third-party component terms before redistribution.

The Linux interpreter was executed from the extracted ORBIT directory, and the shipped `run_linux.sh` was exercised in a live server/restart test. The Windows runtime binary/launcher paths were inspected but **not run**: no Windows environment was available. The package supports only Windows x86_64 and Linux x86_64 GNU; it provides no ARM or macOS runtime.

## Compatibility constraints

The upstream runtime project describes standalone Python distributions with standard-library components and bundled/static library dependencies where applicable. Linux GNU builds still require compatible host GNU libc, the system loader and other OS libraries. “Portable” does not mean that the same executable works on every distribution, architecture, CPU, security policy, or USB filesystem. Linux musl builds are not included. Windows removable-media policy, SmartScreen/antivirus, current supported Windows version, and UCRT/system requirements remain unverified in this environment.

The selected distribution is a standalone runtime archive, not the official Windows “embeddable package.” CPython Windows docs describe the embeddable package as isolated and vendorable, excluding pip/Tcl/docs and not supporting normal pip package management; ORBIT core currently needs no third-party packages. PyInstaller was not selected because target-specific builds are required; the bundled runtime approach keeps source runnable on each supported OS without installing project dependencies.

The ORBIT launcher sets `PYTHONHOME`, `PYTHONPATH`, `PYTHONNOUSERSITE` and UTF-8 mode from its own extracted folder; it does not use `py -3`, global Python or pip. User data and model paths are project-relative. In v0.5, the platform-local optional Python dependencies (Playwright, Pillow and Windows PyAutoGUI/pywin32 set) are vendored under `VENDOR/`; see `VENDOR/README.md` for versions and retained license files. Browser binaries remain a separate user-triggered USB-local download. These dependencies are not required for model-free workspace tasks. Vendoring does not constitute Windows execution verification.

The runtimes are unsigned by ORBIT. The package does not bypass enterprise/removable-media security; if policy blocks execution, stop and follow the device owner's approved process. Verify the downloaded ORBIT archive source/hash and retain upstream runtime hashes above for provenance. No legal opinion is made.

## Manual clean-host test procedure

1. On a clean supported target, copy the full ZIP to a USB drive and extract it without installing Python or modifying PATH/registry.
2. On Windows x64, use a clean Windows installation/VM with Python absent; inspect Process Explorer/command line or Windows Process Monitor to confirm `RUNTIME\WINDOWS\python\python.exe` is launched and no AppData/project installation is created. Double-click `run_windows.bat`; open the local dashboard, run the multi-step report acceptance task, stop, restart, and confirm saved task/file state.
3. On Linux x86_64 GNU, use a supported clean distribution/VM with no project Python packages installed; execute `./run_linux.sh` from the USB path. Confirm the embedded `python3.12` is used, complete the same task, stop/restart, and verify persistence.
4. Confirm `DATA/orbit.sqlite3`, `DATA/workspace/`, `CONFIG/orbit.json`, `LOGS/`, and any backup/model path stay under the extracted directory. Test read-only and low-space drives without risking valuable data. Remove/eject only after closing ORBIT.
5. Record OS build, glibc (Linux), USB filesystem, free space, launch output, process paths and restart results. Report any OS security-policy block rather than bypassing it.

## References

- CPython on Windows, embedded distribution details: https://docs.python.org/3/using/windows.html#the-embeddable-package
- python-build-standalone runtime requirements: https://gregoryszorc.com/docs/python-build-standalone/main/running.html
- python-build-standalone distributions and licensing: https://gregoryszorc.com/docs/python-build-standalone/main/distributions.html
- PyInstaller platform/build behavior: https://pyinstaller.org/en/stable/usage.html
