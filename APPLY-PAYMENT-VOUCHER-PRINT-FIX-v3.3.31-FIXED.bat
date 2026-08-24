@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "PATCH_DIR=%CD%"
set "PROJECT_DIR="

echo ============================================================
echo Ziad Invoices v3.3.31 - Payment Voucher Print Fix
echo Fixed installer - can be run from any folder
echo ============================================================
echo.

rem 1) If a project folder was passed as an argument, use it.
if not "%~1"=="" (
    set "PROJECT_DIR=%~1"
    goto CHECK_PROJECT
)

rem 2) If this patch folder is directly inside the project, use the parent.
for %%I in ("%PATCH_DIR%\..") do set "CANDIDATE=%%~fI"
if exist "%CANDIDATE%\app\static\form-templates" (
    set "PROJECT_DIR=%CANDIDATE%"
    goto CHECK_PROJECT
)

rem 3) If the BAT itself was copied to the project root, use this folder.
if exist "%PATCH_DIR%\app\main.py" if exist "%PATCH_DIR%\app\static\form-templates" (
    set "PROJECT_DIR=%PATCH_DIR%"
    goto CHECK_PROJECT
)

rem 4) Known project location used on this PC.
if exist "C:\Users\User\Desktop\ziad-invoices-v3.3.3\app\static\form-templates" (
    set "PROJECT_DIR=C:\Users\User\Desktop\ziad-invoices-v3.3.3"
    goto CHECK_PROJECT
)

rem 5) Common Desktop location based on the current Windows user.
if exist "%USERPROFILE%\Desktop\ziad-invoices-v3.3.3\app\static\form-templates" (
    set "PROJECT_DIR=%USERPROFILE%\Desktop\ziad-invoices-v3.3.3"
    goto CHECK_PROJECT
)

goto ASK_PROJECT

:ASK_PROJECT
echo The Ziad Invoices project was not found automatically.
echo.
echo Example:
echo C:\Users\User\Desktop\ziad-invoices-v3.3.3
echo.
set /p "PROJECT_DIR=Paste the FULL project folder path here: "
set "PROJECT_DIR=%PROJECT_DIR:"=%"

:CHECK_PROJECT
if not defined PROJECT_DIR goto ASK_PROJECT
if not exist "%PROJECT_DIR%\app\static\form-templates" (
    echo.
    echo ERROR: This is not the Ziad Invoices project folder:
    echo %PROJECT_DIR%
    echo.
    set "PROJECT_DIR="
    goto ASK_PROJECT
)

if not exist "%PATCH_DIR%\app\static\form-templates\payment-voucher.html" (
    echo.
    echo ERROR: Patch file is missing:
    echo %PATCH_DIR%\app\static\form-templates\payment-voucher.html
    echo.
    pause
    exit /b 1
)

echo.
echo Project found:
echo %PROJECT_DIR%
echo.

if exist "%PROJECT_DIR%\app\static\form-templates\payment-voucher.html" (
    copy /Y "%PROJECT_DIR%\app\static\form-templates\payment-voucher.html" "%PROJECT_DIR%\app\static\form-templates\payment-voucher.html.v3.3.31.before-print-fix.backup" >nul
    if errorlevel 1 (
        echo ERROR: Could not create the backup file.
        pause
        exit /b 1
    )
)

copy /Y "%PATCH_DIR%\app\static\form-templates\payment-voucher.html" "%PROJECT_DIR%\app\static\form-templates\payment-voucher.html" >nul
if errorlevel 1 (
    echo ERROR: Could not update payment-voucher.html
    pause
    exit /b 1
)

echo.
echo ============================================================
echo SUCCESS

echo Payment Voucher print alignment fix was installed.
echo Project: %PROJECT_DIR%
echo.
echo Restart Ziad Invoices, press Ctrl+F5 once, then print a

echo Payment Voucher to PDF and verify that all text is above lines.
echo ============================================================
echo.
pause
exit /b 0
