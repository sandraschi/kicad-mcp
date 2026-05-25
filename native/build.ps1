$Root = Split-Path -Parent $PSScriptRoot
$RepoName = Split-Path -Leaf $Root
$BackendPath = "$PSScriptRoot\binaries"
$TargetTriple = "x86_64-pc-windows-msvc"

Write-Host "Building $RepoName native app..." -ForegroundColor Cyan

# Step 1: Build React frontend
Write-Host "[1/4] Building React frontend..." -ForegroundColor Yellow
Push-Location "$Root\webapp"
npm install
npm run build
Pop-Location

# Step 2: Build Python backend as standalone .exe
Write-Host "[2/4] Building Python backend via PyInstaller..." -ForegroundColor Yellow
Push-Location "$Root"
& ".venv\Scripts\python.exe" -m PyInstaller `
    --onedir -y --clean `
    --name "${RepoName}-backend" `
    --add-data "src/${RepoName};${RepoName}" `
    --copy-metadata fastmcp --copy-metadata fastapi `
    --hidden-import uvicorn.logging `
    run_server.py
Pop-Location

# Step 3: Copy sidecar binary for Tauri
Write-Host "[3/4] Copying sidecar binary..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $BackendPath | Out-Null
Copy-Item "$Root\dist\${RepoName}-backend\${RepoName}-backend.exe" `
    "$BackendPath\${RepoName}-backend-${TargetTriple}.exe" -Force

# Step 4: Build Tauri bundle
Write-Host "[4/4] Building Tauri bundle..." -ForegroundColor Yellow
Push-Location $PSScriptRoot
npx @tauri-apps/cli build
Pop-Location

Write-Host "Done! Installer at: native\target\release\bundle\nsis\" -ForegroundColor Green
