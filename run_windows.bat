@echo off
setlocal EnableExtensions
set "ORBIT_ROOT=%~dp0"
set "PYTHONHOME=%ORBIT_ROOT%RUNTIME\WINDOWS\python"
set "PYTHONPATH=%ORBIT_ROOT%"
set "PYTHONNOUSERSITE=1"
set "PYTHONUTF8=1"
set "PLAYWRIGHT_BROWSERS_PATH=%ORBIT_ROOT%RUNTIME\WINDOWS\browser-cache"
set "PLAYWRIGHT_SKIP_BROWSER_GC=1"
if not exist "%PYTHONHOME%\python.exe" (
  echo ORBIT portable Windows runtime was not found at:
  echo   "%PYTHONHOME%\python.exe"
  echo Confirm the full ZIP was extracted and Windows x64 is supported.
  pause
  exit /b 2
)
cd /d "%ORBIT_ROOT%"
echo Starting ORBIT with the bundled Windows x64 Python runtime...
"%PYTHONHOME%\python.exe" -m orbit.app
set "ORBIT_EXIT=%ERRORLEVEL%"
if not "%ORBIT_EXIT%"=="0" (
  echo ORBIT stopped with error %ORBIT_EXIT%. The drive may be read-only, disconnected, or blocked by Windows security policy.
  pause
)
exit /b %ORBIT_EXIT%
