@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Ziad Invoices Professional

set "VENV_PY=%CD%\.venv\Scripts\python.exe"

if not exist "%VENV_PY%" (
    echo [INFO] .venv is missing. Running the one-time dependency repair...
    call "%CD%\APPLY-WINDOWS-DEPENDENCY-FIX.bat"
    if errorlevel 1 exit /b 1
)

"%VENV_PY%" -c "from bs4 import BeautifulSoup; import uvicorn" >nul 2>nul
if errorlevel 1 (
    echo [INFO] Required Python packages are missing. Repairing them now...
    call "%CD%\APPLY-WINDOWS-DEPENDENCY-FIX.bat"
    if errorlevel 1 exit /b 1
)

echo [INFO] Starting Ziad Invoices with the project virtual environment...
"%VENV_PY%" "%CD%\start.py"
set "EXITCODE=%ERRORLEVEL%"

if not "%EXITCODE%"=="0" (
    echo.
    echo [ERROR] Ziad Invoices exited with code %EXITCODE%.
    pause
)

exit /b %EXITCODE%
