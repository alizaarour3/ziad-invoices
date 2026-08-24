@echo off
setlocal
cd /d "%~dp0"
set "PATCH_DIR=%CD%"
cd ..
set "PROJECT_DIR=%CD%"

if not exist "%PROJECT_DIR%\app\static\form-templates" (
  echo ERROR: Put this extracted patch folder directly inside the Ziad Invoices project folder.
  pause
  exit /b 1
)

if exist "%PROJECT_DIR%\app\static\form-templates\payment-voucher.html" (
  copy /Y "%PROJECT_DIR%\app\static\form-templates\payment-voucher.html" "%PROJECT_DIR%\app\static\form-templates\payment-voucher.html.v3.3.31.backup" >nul
)

copy /Y "%PATCH_DIR%\app\static\form-templates\payment-voucher.html" "%PROJECT_DIR%\app\static\form-templates\payment-voucher.html" >nul
if errorlevel 1 (
  echo ERROR: Could not update payment-voucher.html
  pause
  exit /b 1
)

echo.
echo Ziad Invoices v3.3.31 payment voucher print alignment fix applied successfully.
echo Only print positioning inside payment-voucher.html was changed.
echo Restart the system and print a Payment Voucher to PDF.
echo.
pause
