@echo off
rem eMagzines launcher (ASCII only on purpose: cmd parses batch files by byte offset,
rem so all Chinese UI lives in the PowerShell scripts instead).
setlocal
cd /d "%~dp0"

if exist "scripts\_bootstrap.py" (
    where python >nul 2>nul && python "scripts\_bootstrap.py" >nul 2>nul
)

set "PS=powershell"
where pwsh >nul 2>nul && set "PS=pwsh"

"%PS%" -NoProfile -ExecutionPolicy Bypass -File "scripts\menu.ps1"
if errorlevel 1 (
    echo.
    echo [!] menu failed. Run: powershell -NoProfile -File scripts\menu.ps1
    pause
)
exit /b 0
