@echo off
rem eMagzines: remove scheduled task
setlocal
cd /d "%~dp0.."

if exist "%~dp0_bootstrap.py" (
    where python >nul 2>nul && python "%~dp0_bootstrap.py" >nul 2>nul
)

set "PS=powershell"
where pwsh >nul 2>nul && set "PS=pwsh"

"%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0ui_remove.ps1"
if errorlevel 1 (
    echo.
    echo [!] remove failed. Run: powershell -NoProfile -File scripts\remove_task.ps1
    pause
)
exit /b 0
