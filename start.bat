@echo off
setlocal
REM kicad-mcp — KiCad PCB automation MCP
set "REPODIR=%~dp0..\..\kicad-mcp"
if not exist "%REPODIR%\start.ps1" (
  echo [ERROR] kicad-mcp not found. Expected: %REPODIR%\start.ps1
  pause
  exit /b 1
)
cd /d "%REPODIR%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%CD%\start.ps1" %*
endlocal & exit /b %ERRORLEVEL%
