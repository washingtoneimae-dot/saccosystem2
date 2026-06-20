# SACCO Stop — run this in PowerShell to stop the system
Get-Process -ErrorAction SilentlyContinue |
    Where-Object { $_.ProcessName -match "python|py" -and $_.CommandLine -match "api_server" } |
    Stop-Process -Force
Write-Host "SACCO stopped."
