@echo off
setlocal
cd /d "%~dp0"
set "PY="
if exist "%USERPROFILE%\Desktop\ziad-invoices-v3.3.3\.venv\Scripts\python.exe" set "PY=%USERPROFILE%\Desktop\ziad-invoices-v3.3.3\.venv\Scripts\python.exe"
if not defined PY where py >nul 2>nul && set "PY=py -3"
if not defined PY set "PY=python"
if "%~1"=="" (%PY% tools\rollback_v3333.py) else (%PY% tools\rollback_v3333.py --root "%~1")
pause
