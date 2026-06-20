# SACCO Start — run this in PowerShell to start the system
$BaseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $BaseDir
$Port = 9160

# Check if already running
$proc = Get-Process -ErrorAction SilentlyContinue |
    Where-Object { $_.ProcessName -match "python|py" -and $_.CommandLine -match "api_server" }
if ($proc) {
    Write-Host "SACCO is already running!"
    Write-Host "Dashboard: http://127.0.0.1:$Port/dashboard"
    exit
}

Write-Host "Starting SACCO..."
$p = Start-Process -FilePath "python" -ArgumentList "api_server.py" -WindowStyle Hidden -PassThru
Start-Sleep -Seconds 3

# Verify
try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/" -UseBasicParsing -TimeoutSec 2
    Write-Host "SACCO is running! (PID: $($p.Id))"
    Write-Host "Dashboard: http://127.0.0.1:$Port/dashboard"
    Start-Process "http://127.0.0.1:$Port/dashboard"
} catch {
    # Try with py launcher if python failed
    $p2 = Start-Process -FilePath "py" -ArgumentList "api_server.py" -WindowStyle Hidden -PassThru
    Start-Sleep -Seconds 3
    try {
        $r2 = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/" -UseBasicParsing -TimeoutSec 2
        Write-Host "SACCO is running! (PID: $($p2.Id), via py launcher)"
        Write-Host "Dashboard: http://127.0.0.1:$Port/dashboard"
        Start-Process "http://127.0.0.1:$Port/dashboard"
    } catch {
        Write-Host "Failed to start. Check if Python is installed."
    }
}
