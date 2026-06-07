# start.ps1 - KiCad MCP webapp frontend only
param([switch]$NoBrowser)
$ScriptRoot = Split-Path -Parent $PSCommandPath
$FrontendPort = 11017

Get-NetTCPConnection -LocalPort $FrontendPort -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }

Write-Host "Starting KiCad MCP frontend on port $FrontendPort..." -ForegroundColor Cyan
$proc = Start-Process -NoNewWindow -FilePath "npx" -ArgumentList "vite --port $FrontendPort" -WorkingDirectory $ScriptRoot -PassThru

Start-Sleep 3
Start-Process "http://127.0.0.1:$FrontendPort"
Write-Host "Webapp: http://localhost:$FrontendPort" -ForegroundColor Green
$proc.WaitForExit()
