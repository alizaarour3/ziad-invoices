@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Ziad Invoices - Payment Voucher and PR Transfer Fix

echo ============================================================
echo   ZIAD INVOICES v3.3.24 - PAYMENT VOUCHER FIX
echo ============================================================
echo.
echo IMPORTANT: Close Ziad Invoices before applying this patch.
echo.

set "VENV_PY=%CD%\.venv\Scripts\python.exe"
if exist "%VENV_PY%" (
    "%VENV_PY%" "%CD%\tools\apply_payment_voucher_transfer_fix.py"
) else (
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 "%CD%\tools\apply_payment_voucher_transfer_fix.py"
    ) else (
        python "%CD%\tools\apply_payment_voucher_transfer_fix.py"
    )
)

if errorlevel 1 (
    echo.
    echo [ERROR] The patch was not applied.
    echo Extract this ZIP directly into the Ziad Invoices project root.
    echo The same folder must contain the app folder.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   DONE - PAYMENT VOUCHER UPDATED
echo ============================================================
echo.
echo 1. Start Ziad Invoices.
echo 2. Open Payment Voucher and check text is above the lines.
echo 3. Create a Payment Request and convert it to Payment Voucher.
echo 4. Confirm the matching PR values are already in the PV fields.
echo.
pause
exit /b 0
