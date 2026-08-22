@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Ziad Invoices - Windows Dependency Repair

echo ============================================================
echo   ZIAD INVOICES PROFESSIONAL - DEPENDENCY REPAIR v3.3.21
echo ============================================================
echo.

set "VENV_PY=%CD%\.venv\Scripts\python.exe"

if not exist "%VENV_PY%" (
    echo [INFO] Project virtual environment was not found. Creating .venv...
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 -m venv "%CD%\.venv"
    ) else (
        where python >nul 2>nul
        if errorlevel 1 (
            echo [ERROR] Python 3 is not installed or is not available in PATH.
            echo Install Python 3, then run this file again.
            pause
            exit /b 1
        )
        python -m venv "%CD%\.venv"
    )
)

if not exist "%VENV_PY%" (
    echo [ERROR] Could not create or find .venv\Scripts\python.exe
    pause
    exit /b 1
)

echo [INFO] Using project Python only:
echo        %VENV_PY%
echo.

"%VENV_PY%" "%CD%\tools\repair_windows_dependencies.py"
if errorlevel 1 (
    echo.
    echo [ERROR] Repair did not complete. Read the message above.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   REPAIR COMPLETE - bs4 / BeautifulSoup is installed
echo ============================================================
echo.
echo You can now double-click START-ZIAD-INVOICES-SAFE.bat
pause
exit /b 0
