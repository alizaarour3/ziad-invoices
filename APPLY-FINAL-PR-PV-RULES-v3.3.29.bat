@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Ziad Invoices v3.3.29 - Final PR to PV Rules

echo ============================================================
echo  ZIAD INVOICES v3.3.29 - FINAL PR to PV MAPPING + PDF LINES
echo ============================================================
echo.

set "PY=%CD%\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

"%PY%" "%CD%\tools\apply_v3329_final_fix.py"
if errorlevel 1 (
  echo.
  echo [ERROR] Update failed. No voucher template artwork should be changed.
  pause
  exit /b 1
)

echo.
echo ============================================================
echo  COMPLETE - FINAL MAPPING IS LOCKED
 echo  Restart Ziad Invoices, then press Ctrl+F5 once.
echo ============================================================
pause
exit /b 0
