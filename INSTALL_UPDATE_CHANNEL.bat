@echo off
setlocal EnableExtensions
title Signal Lab - Install Update Channel

set "SYSTEM_DIR=C:\Signal-Lab\System"
set "UPDATER=%SYSTEM_DIR%\UPDATE_SIGNAL_LAB.bat"

if not exist "%SYSTEM_DIR%" mkdir "%SYSTEM_DIR%"
if errorlevel 1 (
  echo ERROR: Could not create %SYSTEM_DIR%
  pause
  exit /b 1
)

(
  echo @echo off
  echo setlocal EnableExtensions
  echo title Signal Lab - Update
  echo set "SCRIPT=%%TEMP%%\signal-lab-update-%%RANDOM%%.ps1"
  echo powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -UseBasicParsing -Uri 'https://raw.githubusercontent.com/aviad-jpg/signal-lab-updates/main/update.ps1' -OutFile '%%SCRIPT%%'"
  echo if errorlevel 1 ^(
  echo   echo ERROR: Could not download the updater.
  echo   pause
  echo   exit /b 1
  echo ^)
  echo powershell -NoProfile -ExecutionPolicy Bypass -File "%%SCRIPT%%"
  echo set "RESULT=%%ERRORLEVEL%%"
  echo del /q "%%SCRIPT%%" ^>nul 2^>nul
  echo if not "%%RESULT%%"=="0" ^(
  echo   echo ERROR: Update failed. Send a screenshot of this window.
  echo   pause
  echo   exit /b %%RESULT%%
  echo ^)
  echo echo.
  echo echo Update complete.
  echo pause
) > "%UPDATER%"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut([System.IO.Path]::Combine([Environment]::GetFolderPath('Desktop'),'Signal Lab Update.lnk')); $s.TargetPath='%UPDATER%'; $s.WorkingDirectory='%SYSTEM_DIR%'; $s.Save()"

echo Permanent updater installed:
echo %UPDATER%
echo A shortcut named Signal Lab Update was added to the Desktop.
echo.
echo Running the first update now...
call "%UPDATER%"
exit /b %ERRORLEVEL%
