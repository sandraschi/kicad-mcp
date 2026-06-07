# start.ps1 - KiCad MCP + Webapp (SOTA 2026)
param([switch]$Headless, [switch]$BackendOnly, [switch]$NoBrowser)
$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $PSCommandPath
$BackendPort = 11016
$FrontendPort = 11017
$env:KICAD_MCP_WORK_DIR = "$env:TEMP\kicad_mcp_work"

$FleetStartPath = Join-Path $ScriptRoot "scripts\FleetStartMode.ps1"
if (-not (Test-Path -LiteralPath $FleetStartPath)) {
    Write-Host "ERROR: Missing vendored launcher helper: $FleetStartPath" -ForegroundColor Red
    exit 1
}
. $FleetStartPath
Stop-FleetPortSquatters -Ports @($BackendPort, $FrontendPort, 11018) -Label "kicad-mcp"

Write-Host "Starting KiCad MCP backend on port $BackendPort..." -ForegroundColor Cyan
$backendCmd = "Set-Location '$ScriptRoot'; uv run --project '$ScriptRoot' python -m kicad_mcp.server --mode dual --port $BackendPort"
$BackendProc = Start-Process powershell -ArgumentList "-NoProfile", "-WindowStyle", "Normal", "-Command", $backendCmd -PassThru

Write-Host "Waiting for backend on port $BackendPort..." -ForegroundColor Gray
$backendReady = $false
for ($i = 0; $i -lt 60; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$BackendPort/api/v1/status" -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
        if ($r.StatusCode -eq 200) { $backendReady = $true; break }
    } catch {}
    Start-Sleep 1
}
if ($backendReady) {
    Write-Host "Backend ready on http://127.0.0.1:$BackendPort" -ForegroundColor Green
} else {
    Write-Host "Backend did not return HTTP 200 from /api/v1/status - check logs." -ForegroundColor Yellow
}

if ($BackendOnly) {
    while (-not $BackendProc.HasExited) { Start-Sleep 2 }
    exit
}

$WebRoot = Join-Path $ScriptRoot "webapp"
if (-not (Test-Path (Join-Path $WebRoot "node_modules"))) {
    Set-Location $WebRoot
    npm install
}

if (-not $NoBrowser) {
    $frontendUrl = "http://127.0.0.1:$FrontendPort/"
    $pollAndOpen = "for (`$i = 0; `$i -lt 60; `$i++) { try { `$null = Invoke-WebRequest -Uri '$frontendUrl' -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop; Start-Process '$frontendUrl'; exit } catch { Start-Sleep -Seconds 1 } }"
    Start-Process powershell -ArgumentList "-NoProfile", "-WindowStyle", "Hidden", "-Command", $pollAndOpen
}

Write-Host "KiCad MCP: http://localhost:$BackendPort/api/v1/status" -ForegroundColor Green
Write-Host "Webapp:    http://localhost:$FrontendPort" -ForegroundColor Green
Write-Host "Starting Vite frontend on port $FrontendPort..." -ForegroundColor Green
Set-Location $WebRoot
npm run dev -- --port $FrontendPort --host --strictPort

