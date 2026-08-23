@echo off
setlocal
cd /d "%~dp0"
set "PY=%CD%\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
echo ============================================================
echo Ziad Invoices v3.3.30 - HTML TEMPLATE FIRST
echo Uses the supplied HTML files instead of the legacy image editor.
echo ============================================================
"%PY%" tools\apply_v3330_html_templates.py
if errorlevel 1 (
  echo.
  echo ERROR: update was not completed.
  pause
  exit /b 1
)
echo.
echo DONE. Restart Ziad Invoices, then press Ctrl+F5 once.
echo The voucher/request templates are now loaded as HTML templates.
pause
