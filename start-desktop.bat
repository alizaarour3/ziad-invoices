@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Please run setup-windows.bat first.
  pause
  exit /b 1
)
call ".venv\Scripts\activate.bat"
python desktop.py
endlocal
