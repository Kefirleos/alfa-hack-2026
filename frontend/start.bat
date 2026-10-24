@echo off
setlocal
cd /d "%~dp0"

REM ============================================================
REM  Alfa-Business - frontend launcher
REM  Put this folder into the repository root (next to backend\)
REM  and double-click this file. run.py finds the backend itself,
REM  starts API + static server and opens the browser.
REM  Stop everything with Ctrl+C in this window.
REM ============================================================

set "VENVPY="
for %%D in ("%~dp0..\backend" "%~dp0..\repo\backend") do (
    if not defined VENVPY if exist "%%~fD\.venv\Scripts\python.exe" set "VENVPY=%%~fD\.venv\Scripts\python.exe"
)

if defined VENVPY (
    "%VENVPY%" "%~dp0run.py" %*
    exit /b
)

where python >nul 2>nul
if not errorlevel 1 (
    python "%~dp0run.py" %*
    exit /b
)

where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0run.py" %*
    exit /b
)

echo.
echo [ERROR] Python 3.11 not found. Install Python 3.11 and run this file again.
echo.
pause
exit /b 1
