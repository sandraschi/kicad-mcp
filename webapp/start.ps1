# start.ps1 — KiCad MCP webapp frontend only
param([switch]$NoBrowser)
$ScriptRoot = Split-Path -Parent $PSCommandPath
$ProjectRoot = Split-Path -Parent $ScriptRoot
$FrontendPort = 11017

# Source FleetStartMode for port helpers
$FleetStartPath = Join-Path $ProjectRoot "scripts\FleetStartMode.ps1"
if (Test-Path -LiteralPath $FleetStartPath) {
    . $FleetStartPath
}

Get-NetTCPConnection -LocalPort $FrontendPort -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }

Write-Host "Starting KiCad MCP frontend on port $FrontendPort..." -ForegroundColor Cyan
$proc = Start-Process -NoNewWindow -FilePath "npx" -ArgumentList "vite --port $FrontendPort" -WorkingDirectory $ScriptRoot -PassThru

Start-Sleep 3
if (-not $NoBrowser) {
    Start-Process "http://127.0.0.1:$FrontendPort"
}
Write-Host "Webapp: http://localhost:$FrontendPort" -ForegroundColor Green
$proc.WaitForExit()

