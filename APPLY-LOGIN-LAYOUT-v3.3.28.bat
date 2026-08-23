@echo off
setlocal
cd /d "%~dp0"
set "PYTHON="
if exist ".venv\Scripts\python.exe" set "PYTHON=.venv\Scripts\python.exe"
if not defined PYTHON if exist "..\.venv\Scripts\python.exe" set "PYTHON=..\.venv\Scripts\python.exe"
if not defined PYTHON set "PYTHON=python"

echo.
echo ===========================================================
echo  Ziad Invoices v3.3.28 - LOGIN LAYOUT RATIO FIX
echo  LEFT: 66.67%%   RIGHT: 33.33%%
echo  UI ONLY - VOUCHER TEMPLATES ARE NOT MODIFIED
echo  100%% SIZE - NO ZOOM OUT
echo ===========================================================
echo.
"%PYTHON%" "%~dp0tools\apply_login_layout_v3328.py"
if errorlevel 1 (
  echo.
  echo Installation FAILED safely. Read the error above.
  pause
  exit /b 1
)
echo.
echo Installation completed successfully.
echo Restart Ziad Invoices and press Ctrl+F5 once.
pause
