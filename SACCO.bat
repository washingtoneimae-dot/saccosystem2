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
    echo   ERROR: Port %SACCO_PORT% is already in use by another program.
    echo   Close the other program or change SACCO_PORT in SACCO.bat
    pause
    exit /b 1
)

REM ── Step 1: Check Python ──
echo [1/2] Checking Python...

REM Try py first (Windows launcher), then python
set PYTHON_CMD=python
py --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py
    for /f "tokens=2" %%i in ('py --version 2^>^&1') do set "PY_VER=%%i"
    echo   Python %PY_VER% found (via py launcher) [OK]
) else (
    python --version >nul 2>&1
    if %errorlevel% equ 0 (
        for /f "tokens=2" %%i in ('python --version 2^>^&1') do set "PY_VER=%%i"
        echo   Python %PY_VER% found [OK]
    ) else (
        echo.
        echo   ERROR: Python not found!
        echo.
        echo   Install Python from the Microsoft Store or:
        echo   https://www.python.org/downloads/
        echo.
        echo   Make sure to check "Add Python to PATH" during install.
        pause
        exit /b 1
    )
)
echo.

REM ── Step 2: Start Server (with visible errors) ──
echo [2/2] Starting SACCO...
echo   Server log: server.log (check this if something goes wrong)

REM Start server, save errors to server.log instead of hiding them
start /B "" %PYTHON_CMD% api_server.py >server.log 2>&1

REM Wait for server to start
timeout /t 3 /nobreak >nul

REM Verify server actually started
tasklist /fi "IMAGENAME eq python.exe" 2>nul | findstr /i python >nul
if %errorlevel% neq 0 (
    echo.
    echo   ERROR: Server failed to start!
    echo   Check server.log for details.
    echo.
    type server.log 2>nul
    echo.
    pause
    exit /b 1
)

REM Verify port is open
netstat -an | findstr ":%SACCO_PORT% " >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo   WARNING: Server started but port %SACCO_PORT% is not open yet.
    echo   Check server.log if the dashboard doesn't load.
    echo.
)

REM ── Open Dashboard ──
start http://127.0.0.1:%SACCO_PORT%/dashboard
echo.
echo   SACCO is running!
echo   Dashboard: http://127.0.0.1:%SACCO_PORT%/dashboard
echo.
echo   Close the system from the dashboard or close this window.
echo   Server log: server.log
echo.

REM ── Wait for server to stop ──
:waitloop
timeout /t 3 /nobreak >nul
tasklist /fi "IMAGENAME eq python.exe" 2>nul | findstr /i python >nul
if %errorlevel% equ 0 goto waitloop

echo   SACCO stopped.
timeout /t 2 /nobreak >nul
