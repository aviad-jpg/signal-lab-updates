@echo off
setlocal EnableExtensions
title Signal Lab - Retrospective Validation v6

set "APP_DIR=C:\Signal-Lab\System\Signal_Lab_Shadow"
set "PYTHON_CMD=python"
where python >nul 2>nul
if errorlevel 1 set "PYTHON_CMD=py -3"

for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set "STAMP=%%I"
set "OUT=%APP_DIR%\runs\backtest_v6_%STAMP%"
set "ZIP=%OUT%.zip"

if not exist "%APP_DIR%\backtest_manifest.json" (
  echo ERROR: backtest_manifest.json is missing. Run Signal Lab Update first.
  pause
  exit /b 1
)

cd /d "%APP_DIR%"
echo Running version 6 on eight historical days...
echo This can take several minutes.
%PYTHON_CMD% backtest.py --manifest backtest_manifest.json --output-dir "%OUT%"
if errorlevel 1 (
  echo ERROR: Backtest failed. Send a screenshot of this window.
  pause
  exit /b 1
)

powershell -NoProfile -Command "Compress-Archive -LiteralPath '%OUT%' -DestinationPath '%ZIP%' -Force"
if errorlevel 1 (
  echo ERROR: Results were created but ZIP creation failed.
  start "" explorer.exe "%OUT%"
  pause
  exit /b 1
)

echo.
echo COMPLETE
echo Result: %ZIP%
start "" explorer.exe /select,"%ZIP%"
pause
