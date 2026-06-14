@echo off
cd /d "%~dp0"
title SACCO System
set SACCO_PORT=9160

echo.
echo ==============================
echo   SACCO Member Statement System
echo ==============================
echo.

REM ── Check if port is already in use ──
netstat -an | findstr ":%SACCO_PORT% " >nul 2>&1
if %errorlevel% equ 0 (
    echo   Port %SACCO_PORT% is already in use.
    exit /b 1
)

REM ── Step 1: Check Python ──
echo [1/2] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   Python not found! Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set "PY_VER=%%i"
echo   Python %PY_VER% found [OK]
echo.

REM ── Step 2: Start Server ──
echo [2/2] Starting SACCO...
start /B python api_server.py >nul 2>&1
timeout /t 3 /nobreak >nul

REM ── Open Dashboard ──
start http://127.0.0.1:%SACCO_PORT%/dashboard
echo.
echo   SACCO is running!
echo   Dashboard: http://127.0.0.1:%SACCO_PORT%/dashboard
echo.
echo   Close the system from the dashboard or close this window.
echo.

REM ── Wait for server to stop (checks every 3 seconds) ──
:waitloop
timeout /t 3 /nobreak >nul
tasklist /fi "IMAGENAME eq python.exe" 2>nul | findstr /i python >nul
if %errorlevel% equ 0 goto waitloop

echo   SACCO stopped.
timeout /t 2 /nobreak >nul
