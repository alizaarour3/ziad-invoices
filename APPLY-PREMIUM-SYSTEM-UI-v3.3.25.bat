@echo off
setlocal
cd /d "%~dp0"
echo.
echo =============================================================
echo   Ziad Invoices v3.3.25 - Premium System UI
echo   System design only - voucher templates stay unchanged

echo =============================================================
echo.
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" "tools\apply_premium_ui_v3325.py"
) else (
  python "tools\apply_premium_ui_v3325.py"
)
set ERR=%ERRORLEVEL%
echo.
if not "%ERR%"=="0" (
  echo Installation failed. Nothing should be changed except a safe backup.
) else (
  echo Done. Restart Ziad Invoices and press Ctrl+0 once if the browser itself was manually zoomed.
)
echo.
pause
exit /b %ERR%
