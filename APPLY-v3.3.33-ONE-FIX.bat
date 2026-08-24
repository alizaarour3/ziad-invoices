@echo off
setlocal
cd /d "%~dp0"
set "PY="
if exist "%USERPROFILE%\Desktop\ziad-invoices-v3.3.3\.venv\Scripts\python.exe" set "PY=%USERPROFILE%\Desktop\ziad-invoices-v3.3.3\.venv\Scripts\python.exe"
if not defined PY if exist "..\.venv\Scripts\python.exe" set "PY=..\.venv\Scripts\python.exe"
if not defined PY where py >nul 2>nul && set "PY=py -3"
if not defined PY set "PY=python"

if "%~1"=="" (
  %PY% tools\apply_v3333.py
) else (
  %PY% tools\apply_v3333.py --root "%~1"
)
if errorlevel 1 (
  echo.
  echo FAILED. Read the error above.
  pause
  exit /b 1
)
echo.
echo Done. Restart Ziad Invoices and press Ctrl+F5 once.
pause
