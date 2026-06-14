# SACCO Start — run this in PowerShell to start the system
$BaseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $BaseDir

# Check if already running
$proc = Get-Process -Name "python*" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match "api_server" }
if ($proc) {
    Write-Host "SACCO is already running!"
    Write-Host "Dashboard: http://127.0.0.1:9150/dashboard"
    exit
}

Write-Host "Starting SACCO..."
$p = Start-Process -FilePath "python" -ArgumentList "api_server.py" -WindowStyle Hidden -PassThru
Start-Sleep -Seconds 3

# Verify
try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:9150/" -UseBasicParsing -TimeoutSec 2
    Write-Host "SACCO is running! (PID: $($p.Id))"
    Write-Host "Dashboard: http://127.0.0.1:9150/dashboard"
    Start-Process "http://127.0.0.1:9150/dashboard"
} catch {
    Write-Host "Failed to start. Check if Python is installed."
}
