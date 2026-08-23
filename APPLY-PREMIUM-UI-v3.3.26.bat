@echo off
setlocal
cd /d "%~dp0"
set "PYTHON="
if exist ".venv\Scripts\python.exe" set "PYTHON=.venv\Scripts\python.exe"
if not defined PYTHON if exist "..\.venv\Scripts\python.exe" set "PYTHON=..\.venv\Scripts\python.exe"
if not defined PYTHON set "PYTHON=python"

echo.
echo ===========================================================
echo  Ziad Invoices v3.3.26 - PREMIUM UI ONLY
echo  Templates are protected and must remain unchanged.
echo  Application size remains 100%% - no zoom-out.
echo ===========================================================
echo.
"%PYTHON%" "%~dp0tools\apply_premium_ui_v3326.py"
if errorlevel 1 (
  echo.
  echo Installation FAILED safely. Read the error above.
  pause
  exit /b 1
)
echo.
echo Installation completed successfully.
echo Restart Ziad Invoices and press Ctrl+F5 once in the browser.
pause
