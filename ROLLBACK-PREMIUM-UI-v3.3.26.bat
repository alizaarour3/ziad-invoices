@echo off
setlocal
cd /d "%~dp0"
set "PYTHON="
if exist ".venv\Scripts\python.exe" set "PYTHON=.venv\Scripts\python.exe"
if not defined PYTHON if exist "..\.venv\Scripts\python.exe" set "PYTHON=..\.venv\Scripts\python.exe"
if not defined PYTHON set "PYTHON=python"
"%PYTHON%" "%~dp0tools\rollback_premium_ui_v3326.py"
pause
