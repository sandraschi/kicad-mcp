# start.ps1 — KiCad MCP + Webapp (SOTA 2026)
param([switch]$Headless, [switch]$BackendOnly, [switch]$NoBrowser)
$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $PSCommandPath
$BackendPort = 11016
$FrontendPort = 11017
$env:KICAD_MCP_WORK_DIR = "$env:TEMP\kicad_mcp_work"

# Port zombie clearing
Get-NetTCPConnection -LocalPort $BackendPort -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
Get-NetTCPConnection -LocalPort $FrontendPort -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
Get-NetTCPConnection -LocalPort 11018 -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }

# Start backend via Start-Job with proper working directory
$BackendJob = Start-Job -Name "kicad-mcp-backend" -ScriptBlock {
    param($Root, $Port)
    Set-Location $Root
    uv run python -m kicad_mcp.server --mode dual --port $Port
} -ArgumentList $ScriptRoot, $BackendPort

# Readiness poll
Write-Host "Waiting for backend on port $BackendPort..." -ForegroundColor Cyan
for ($i = 0; $i -lt 60; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$BackendPort/api/v1/status" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
        if ($r.StatusCode -eq 200) { break }
    } catch {}
    Start-Sleep 1
}

if (-not $BackendOnly) {
    $WebRoot = Join-Path $ScriptRoot "webapp"
    Start-Process -NoNewWindow -FilePath "npx" -ArgumentList "vite --port $FrontendPort" -WorkingDirectory $WebRoot

    if (-not $NoBrowser) {
        for ($i = 0; $i -lt 30; $i++) {
            try {
                $r = Invoke-WebRequest -Uri "http://127.0.0.1:$FrontendPort" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
                if ($r.StatusCode -eq 200) { break }
            } catch {}
            Start-Sleep 1
        }
        Start-Process "http://127.0.0.1:$FrontendPort"
    }
}

Write-Host "KiCad MCP: http://localhost:$BackendPort/api/v1/status" -ForegroundColor Green
Write-Host "Webapp:    http://localhost:$FrontendPort" -ForegroundColor Green
Write-Host "MCP SSE:   http://localhost:$BackendPort/sse" -ForegroundColor Green

# Keep-alive
while ($true) {
    if ($BackendJob.State -eq "Completed" -or $BackendJob.State -eq "Failed") {
        Receive-Job $BackendJob
        break
    }
    Start-Sleep 2
}
