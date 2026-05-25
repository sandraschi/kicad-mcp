# Installation

## Prerequisites

1. Install KiCad 8.0+ from https://www.kicad.org/download/windows/
2. Ensure `kicad-cli.exe` is on PATH or set `KICAD_CLI_PATH` env var
3. Python 3.12+ with `uv` installed

## Setup

```powershell
# Clone and bootstrap
Set-Location D:\Dev\repos\kicad-mcp
just setup
```

## Running

```powershell
# Start backend (dual mode: REST + MCP SSE)
just serve

# Start with Vite webapp
just web  # in another terminal

# Or use the combined start script
.\start.ps1
```

## TCP Bridge (Optional)

For pcbnew-level board manipulation (component inspection, net listing, track routing),
run the KiCad bridge inside KiCad's Python console:

1. Open KiCad PCB Editor
2. Tools → Scripting Console
3. Run: `exec(open(r"D:\Dev\repos\kicad-mcp\src\kicad_mcp\kc_bridge.py").read())`

The server will auto-detect the bridge on port 11014.
