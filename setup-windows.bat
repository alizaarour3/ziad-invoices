@echo off
setlocal
cd /d "%~dp0"
py -3 -m venv .venv
if errorlevel 1 goto :error
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements-windows.txt
if errorlevel 1 goto :error
echo.
echo Setup completed successfully.
echo Run start-desktop.bat to launch the system.
pause
exit /b 0
:error
echo.
echo Setup failed. Check Python 3.11 or newer and internet access.
pause
exit /b 1
