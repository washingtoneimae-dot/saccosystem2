@echo off
cd /d "%~dp0"
title SACCO System
set SACCO_PORT=9160

echo.
echo ==============================
echo   SACCO Member Statement System
echo ==============================
echo.

REM -- Check if port is already in use --
netstat -an | findstr ":%SACCO_PORT% " >nul 2>&1
if %errorlevel% equ 0 (
    echo   ERROR: Port %SACCO_PORT% is already in use.
    echo   Close the other program or change SACCO_PORT.
    pause
    exit /b 1
)

REM -- Step 1: Check Python --
echo [1/3] Checking Python...

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
        echo   ERROR: Python not found.
        echo   Install from https://www.python.org/downloads/
        pause
        exit /b 1
    )
)
echo.

REM -- Step 2: Check Himalaya CLI (for email) --
echo [2/3] Checking Himalaya CLI...

where himalaya >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('himalaya --version 2^>^&1 ^| findstr /i "himalaya"') do set "HIM_VER=%%i"
    echo   Himalaya found [OK]
) else (
    echo   Himalaya not found. Attempting auto-install...
    echo.
    set "HIM_DIR=%APPDATA%\himalaya\bin"
    if not exist "%HIM_DIR%" mkdir "%HIM_DIR%"

    echo   Downloading latest Himalaya release...
    powershell -Command "& {
        $url = 'https://api.github.com/repos/soywod/himalaya/releases/latest'
        $release = Invoke-RestMethod -Uri $url -Headers @{'User-Agent'='SACCO'}
        $asset = $release.assets | Where-Object { $_.name -like '*windows*' -or $_.name -like '*win64*' }
        if (-not $asset) { $asset = $release.assets[0] }
        $dl = $asset.browser_download_url
        Write-Host \"   Downloading: $dl\"
        $zip = \"%TEMP%\himalaya.zip\"
        Invoke-WebRequest -Uri $dl -OutFile $zip
        Expand-Archive -Path $zip -DestinationPath \"%HIM_DIR%\" -Force
        Remove-Item $zip
        Write-Host \"   Extracted to: %HIM_DIR%\"
    }" 2>&1

    if %errorlevel% equ 0 (
        set "PATH=%HIM_DIR%;%PATH%"
        powershell -Command "[Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path', 'User') + ';%HIM_DIR%', 'User')" >nul 2>&1

        where himalaya >nul 2>&1
        if %errorlevel% equ 0 (
            echo   Himalaya installed [OK]
        ) else (
            echo   WARNING: Himalaya installed but not found in PATH.
            echo   Email features will be disabled.
            echo.
        )
    ) else (
        echo   WARNING: Auto-install failed. Email features disabled.
        echo   Install manually from: https://github.com/soywod/himalaya/releases
        echo.
    )
)
echo.

REM -- Step 3: Start Server --
echo [3/3] Starting SACCO...
echo   Server log: server.log

start /B "" %PYTHON_CMD% api_server.py >server.log 2>&1

echo   Waiting for server...

set /a TRIES=0
:wait_start
timeout /t 2 /nobreak >nul
set /a TRIES+=1

netstat -an | findstr ":%SACCO_PORT% " >nul 2>&1
if %errorlevel% equ 0 goto server_running

if %TRIES% LSS 8 goto wait_start

echo.
echo   ERROR: Server failed to start.
echo   Check server.log for details:
echo   ----------------------------------------
type server.log 2>nul
echo   ----------------------------------------
pause
exit /b 1

:server_running
echo   Server is listening on port %SACCO_PORT% [OK]
echo.

REM -- Open Dashboard --
start http://127.0.0.1:%SACCO_PORT%/dashboard
echo   SACCO is running!
echo   Dashboard: http://127.0.0.1:%SACCO_PORT%/dashboard
echo.
echo   Close this window or press Ctrl+C to stop the server.
echo.

REM -- Wait for server to stop --
:waitloop
timeout /t 3 /nobreak >nul
netstat -an | findstr ":%SACCO_PORT% " >nul 2>&1
if %errorlevel% equ 0 goto waitloop

echo.
echo   SACCO stopped.
timeout /t 3 /nobreak >nul
