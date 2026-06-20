@echo off
echo ===== DEBUG: Batch started at %time% =====
echo Current directory: %cd%
echo Script location: %~dp0
echo.
echo If you can read this, the batch IS executing.
echo Press Enter to continue...
pause >nul

cd /d "%~dp0"
title SACCO System
set SACCO_PORT=9160

echo.
echo ==============================
echo   SACCO Member Statement System
echo ==============================
echo.

REM ── Check if port is already in use ──
echo [PRE] Checking port %SACCO_PORT%...
netstat -an | findstr ":%SACCO_PORT% " >nul 2>&1
if %errorlevel% equ 0 (
    echo   ERROR: Port %SACCO_PORT% is already in use.
    pause
    exit /b 1
)

REM ── Step 1: Check Python ──
echo [1/3] Checking Python...

set PYTHON_CMD=python
echo   Trying py launcher...
py --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py
    for /f "tokens=2" %%i in ('py --version 2^>^&1') do set "PY_VER=%%i"
    echo   Python %PY_VER% found (via py launcher) [OK]
) else (
    echo   py not found, trying python...
    python --version >nul 2>&1
    if %errorlevel% equ 0 (
        for /f "tokens=2" %%i in ('python --version 2^>^&1') do set "PY_VER=%%i"
        echo   Python %PY_VER% found [OK]
    ) else (
        echo   ERROR: Python not found!
        pause
        exit /b 1
    )
)
echo   Python command: %PYTHON_CMD%
echo.

REM ── Step 2: Check Himalaya ──
echo [2/3] Checking Himalaya CLI...
where himalaya >nul 2>&1
if %errorlevel% equ 0 (
    echo   Himalaya found [OK]
) else (
    echo   Himalaya not found (email disabled) [OK]
)
echo.

REM ── Step 3: Start Server ──
echo [3/3] Starting SACCO...
echo   Command: start /B "" %PYTHON_CMD% api_server.py
echo.
echo   Starting server NOW. If window closes after this, check server.log
echo   in this folder for the error.
echo.

start /B "" %PYTHON_CMD% api_server.py >server.log 2>&1

echo   Waiting for port %SACCO_PORT% to open...
set /a TRIES=0
:wait_start
timeout /t 2 /nobreak >nul
set /a TRIES+=1

netstat -an | findstr ":%SACCO_PORT% " >nul 2>&1
if %errorlevel% equ 0 goto server_running

if %TRIES% LSS 8 goto wait_start

REM Server didn't start
echo.
echo ========================================
echo   ERROR: Server did not start!
echo ========================================
echo.
echo   Contents of server.log:
echo   ----------------------------------------
type server.log 2>nul
echo   ----------------------------------------
echo.
echo   Try running this command manually:
echo     %PYTHON_CMD% api_server.py
echo.
pause
exit /b 1

:server_running
echo.
echo   =================================
echo     SACCO IS RUNNING!
echo     Dashboard: http://127.0.0.1:%SACCO_PORT%/dashboard
echo   =================================
echo.
start http://127.0.0.1:%SACCO_PORT%/dashboard

echo   Polling port every 3s... Press Ctrl+C or close window to stop.
echo.

:waitloop
timeout /t 3 /nobreak >nul
netstat -an | findstr ":%SACCO_PORT% " >nul 2>&1
if %errorlevel% equ 0 goto waitloop

echo.
echo   SACCO stopped.
pause
