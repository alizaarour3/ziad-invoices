@echo off
setlocal
cd /d "%~dp0"
set "PY="
if exist "%USERPROFILE%\Desktop\ziad-invoices-v3.3.3\.venv\Scripts\python.exe" set "PY=%USERPROFILE%\Desktop\ziad-invoices-v3.3.3\.venv\Scripts\python.exe"
if not defined PY where py >nul 2>nul && set "PY=py -3"
if not defined PY set "PY=python"

echo ============================================================
echo Ziad Invoices v3.3.33-R2 Installer
echo CLOSE Ziad Invoices before continuing.
echo Also close its server CMD/PowerShell window if it is running.
echo ============================================================
echo.
pause

if "%~1"=="" (
  %PY% tools\apply_v3333_r2.py
) else (
  %PY% tools\apply_v3333_r2.py --root "%~1"
)
if errorlevel 1 (
  echo.
  echo FAILED. If a LOCKED FILE was shown, close the listed app and run this installer again.
  pause
  exit /b 1
)
echo.
echo Done. Start Ziad Invoices again and press Ctrl+F5 once.
pause
