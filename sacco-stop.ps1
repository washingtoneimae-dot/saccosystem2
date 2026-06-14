# SACCO Stop
Get-Process -Name "python*" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match "api_server" } | Stop-Process -Force
Write-Host "SACCO stopped."
