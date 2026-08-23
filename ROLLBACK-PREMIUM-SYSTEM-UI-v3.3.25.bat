@echo off
setlocal
cd /d "%~dp0"
echo Removing Ziad Invoices Premium System UI v3.3.25...
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" "tools\rollback_premium_ui_v3325.py"
) else (
  python "tools\rollback_premium_ui_v3325.py"
)
echo.
pause
