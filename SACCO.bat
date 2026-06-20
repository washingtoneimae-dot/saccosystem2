@echo off
echo STEP 1 - Batch started
pause
echo STEP 2 - Changing directory
cd /d "%~dp0"
pause
echo STEP 3 - Setting port
set SACCO_PORT=9160
pause
echo STEP 4 - Checking port
netstat -an | findstr ":9160 " >nul 2>&1
echo Netstat exit code: %errorlevel%
pause
echo STEP 5 - Checking Python
py --version >nul 2>&1
if %errorlevel% equ 0 (echo Python found via py) else (echo py failed, trying python & python --version >nul 2>&1 & if %errorlevel% equ 0 (echo Python found) else (echo NO PYTHON & pause & exit /b 1))
pause
echo STEP 6 - Starting server
start /B "" python api_server.py >server.log 2>&1
echo Server started, waiting...
timeout /t 3 /nobreak >nul
pause
echo STEP 7 - Opening browser
start http://127.0.0.1:9160/dashboard
echo Done. Close this window to stop server.
pause
