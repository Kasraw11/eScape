@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-escape.ps1"
if errorlevel 1 (
  echo.
  echo eScape did not start successfully. Review the message above.
  pause
  exit /b 1
)
echo.
pause
