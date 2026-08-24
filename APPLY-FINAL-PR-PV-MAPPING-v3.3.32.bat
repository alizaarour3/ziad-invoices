@echo off
setlocal
cd /d "%~dp0"
set "PY="
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
if not defined PY if exist "..\.venv\Scripts\python.exe" set "PY=..\.venv\Scripts\python.exe"
if not defined PY set "PY=python"
%PY% tools\apply_v3332_mapping.py
if errorlevel 1 (
  echo.
  echo FAILED - no changes should be trusted. Read the message above.
  pause
  exit /b 1
)
echo.
echo Ziad Invoices v3.3.32 mapping fix installed successfully.
echo Department from Payment Request now goes to Pay to in Payment Voucher.
echo Pay to from Payment Request now goes to Purpose in Payment Voucher.
pause
