@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" exit /b 1
".venv\Scripts\python.exe" -c "from app.db import init_db; from app.services.backup_service import create_backup; init_db(); print(create_backup())"
endlocal
