@echo off
rem eMagzines: fetch now (manual run)
setlocal
cd /d "%~dp0.."

if exist "%~dp0_bootstrap.py" (
    where python >nul 2>nul && python "%~dp0_bootstrap.py" >nul 2>nul
)

set "PS=powershell"
where pwsh >nul 2>nul && set "PS=pwsh"

"%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0menu_fetch.ps1"
if errorlevel 1 (
    echo.
    echo [!] fetch failed. See logs\ or run: powershell -NoProfile -File scripts\run_fetch.ps1
    pause
)
exit /b 0
