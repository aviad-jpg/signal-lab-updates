@echo off
setlocal EnableExtensions
set "APP_DIR=C:\Signal-Lab\System\Signal_Lab_Shadow"
set "LOG_DIR=%APP_DIR%\logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "PYTHON_CMD=python"
where python >nul 2>nul
if errorlevel 1 set "PYTHON_CMD=py -3"
cd /d "%APP_DIR%"
echo [%date% %time%] Daily Shadow check >> "%LOG_DIR%\daily_shadow.log"
%PYTHON_CMD% run_today_shadow.py --automatic >> "%LOG_DIR%\daily_shadow.log" 2>&1
exit /b %errorlevel%
