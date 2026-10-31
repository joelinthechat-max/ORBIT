@echo off
setlocal EnableExtensions
set "ORBIT_ROOT=%~dp0"
set "PYTHONHOME=%ORBIT_ROOT%RUNTIME\WINDOWS\python"
set "PYTHONPATH=%ORBIT_ROOT%;%ORBIT_ROOT%VENDOR\WINDOWS"
set "PYTHONNOUSERSITE=1"
set "PLAYWRIGHT_BROWSERS_PATH=%ORBIT_ROOT%RUNTIME\WINDOWS\browser-cache"
set "PLAYWRIGHT_SKIP_BROWSER_GC=1"
if not exist "%PYTHONHOME%\python.exe" (
  echo Bundled Windows runtime missing: "%PYTHONHOME%\python.exe"
  exit /b 2
)
echo This downloads Playwright's pinned Chromium build into the ORBIT USB folder:
echo   "%PLAYWRIGHT_BROWSERS_PATH%"
echo Host Windows policies may prevent execution. No administrator install is attempted.
"%PYTHONHOME%\python.exe" -m playwright install chromium
