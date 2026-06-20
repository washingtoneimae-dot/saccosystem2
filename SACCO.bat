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
echo [1/3] Checking Python...

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

REM ── Step 2: Check Himalaya CLI (for email) ──
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

    REM Download latest Himalaya Windows release from GitHub
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
        REM Add to PATH for this session and permanently
        set "PATH=%HIM_DIR%;%PATH%"
        powershell -Command "[Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path', 'User') + ';%HIM_DIR%', 'User')" >nul 2>&1

        where himalaya >nul 2>&1
        if %errorlevel% equ 0 (
            echo   Himalaya installed successfully [OK]
        ) else (
            echo.
            echo   WARNING: Himalaya downloaded but not found in PATH.
            echo   The system will work without email.
            echo   To fix manually, add this to your PATH:
            echo     %HIM_DIR%
            echo.
        )
    ) else (
        echo.
        echo   WARNING: Automatic Himalaya install failed.
        echo   The system will work, but email features will be disabled.
        echo.
        echo   To install manually:
        echo   1. Download from: https://github.com/soywod/himalaya/releases
        echo   2. Extract himalaya.exe to a folder
        echo   3. Add that folder to your PATH
        echo.
        echo   Or if you have Scoop: scoop install himalaya
        echo   Or if you have Winget: winget install himalaya
        echo.
    )
)
echo.

REM ── Step 3: Start Server (with visible errors) ──
echo [3/3] Starting SACCO...
echo   Server log: server.log (check this if something goes wrong)

REM Start server, save errors to server.log instead of hiding them
start /B "" %PYTHON_CMD% api_server.py >server.log 2>&1

REM Wait for server to start
timeout /t 3 /nobreak >nul

REM Verify server actually started
tasklist /v /fi "STATUS eq running" 2>nul | findstr /i "python py.exe" >nul
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
tasklist /v /fi "STATUS eq running" 2>nul | findstr /i "python py.exe" >nul
if %errorlevel% equ 0 goto waitloop

echo   SACCO stopped.
echo   Press any key to close.
pause >nul
