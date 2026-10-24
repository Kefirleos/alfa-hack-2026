@echo off
setlocal
cd /d "%~dp0"

REM ============================================================
REM  Alfa-Business - stop
REM  Kills whatever listens on API (8000) and site (5173) ports.
REM  Use it if the launcher window is already closed.
REM ============================================================

echo === Stopping Alfa-Business (API 8000, site 5173) ===

set "FOUND="
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    set "FOUND=1"
    echo Killing API process PID %%p
    taskkill /F /T /PID %%p >nul 2>nul
)

for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do (
    set "FOUND=1"
    echo Killing site process PID %%p
    taskkill /F /T /PID %%p >nul 2>nul
)

if not defined FOUND echo Nothing is running on ports 8000 and 5173.

echo.
echo Done.
echo.
pause
exit /b 0
