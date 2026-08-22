@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Ziad Invoices - Login 100 Percent Size Fix

echo ============================================================
echo   ZIAD INVOICES - LOGIN FULL SIZE FIX v3.3.22
echo ============================================================
echo.

set "VENV_PY=%CD%\.venv\Scripts\python.exe"
if exist "%VENV_PY%" (
    "%VENV_PY%" "%CD%\tools\apply_login_size_fix.py"
) else (
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 "%CD%\tools\apply_login_size_fix.py"
    ) else (
        python "%CD%\tools\apply_login_size_fix.py"
    )
)

if errorlevel 1 (
    echo.
    echo [ERROR] The UI patch was not applied.
    echo Make sure this ZIP is extracted directly into the project root.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   DONE - LOGIN PAGE LOCKED TO FULL 100 PERCENT VISUAL SIZE
echo ============================================================
echo.
echo Restart Ziad Invoices now.
echo If the browser itself was manually zoomed, press Ctrl+0 once.
pause
exit /b 0
