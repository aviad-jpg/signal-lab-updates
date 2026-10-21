@echo off
setlocal
cd /d "%~dp0"
py -3 collect_shadow_results.py
if errorlevel 1 (
  echo.
  echo No completed Shadow results are available yet.
  pause
)
endlocal
