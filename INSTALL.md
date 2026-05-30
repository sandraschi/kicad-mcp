# Installation

## Prerequisites

1. **KiCad 10.0.x stable** — https://www.kicad.org/download/windows/  
   Provides production-trusted `kicad-cli` for exports, DRC, ERC.
2. **KiCad 11 dev nightly** (optional but required for headless CRUD) — https://downloads.kicad.org/kicad/windows/explore/nightlies  
   Install side-by-side; do not remove 10.0.x.
3. Python 3.12+ with `uv` — https://docs.astral.sh/uv/

## Setup

```powershell
Set-Location D:\Dev\repos\kicad-mcp
just bootstrap
# For headless IPC CRUD:
uv sync --extra ipc
```

## Environment (hybrid install)

| Variable | Example | Purpose |
|----------|---------|---------|
| `KICAD_CLI_PATH` | `C:/Program Files/KiCad/10.0/bin/kicad-cli.exe` | Stable export lane |
| `KICAD_IPC_CLI_PATH` | `C:/Program Files/KiCad/11.0/bin/kicad-cli.exe` | Nightly IPC lane |
| `KICAD_MCP_CRUD_BACKEND` | `auto` | `auto` \| `ipc` \| `tcp` \| `none` |

Full guide: [docs/NIGHTLY_HEADLESS.md](docs/NIGHTLY_HEADLESS.md)

## Verify install

```powershell
uv run python -m kicad_mcp.scripts.probe_ipc_headless
uv run pytest tests -q
```

## Running

```powershell
# Backend (REST + MCP SSE) — set hybrid env first if using IPC
just serve

# Cursor stdio MCP
uv run --extra ipc python -m kicad_mcp.server --mode stdio

# Webapp (second terminal)
just web
# Or: .\start.ps1
```

Opens dashboard at http://localhost:11017 (backend on 11016).

## CRUD backends (pick one or use auto)

### A — Headless IPC (recommended when nightly installed)

```powershell
uv sync --extra ipc
$env:KICAD_CLI_PATH = "C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
$env:KICAD_IPC_CLI_PATH = "C:\Program Files\KiCad\11.0\bin\kicad-cli.exe"
$env:KICAD_MCP_CRUD_BACKEND = "auto"
uv run --extra ipc python -m kicad_mcp.server --mode stdio
```

### B — Legacy TCP bridge (KiCad 10 GUI)

1. Open KiCad PCB Editor
2. Tools → Scripting Console
3. Run: `exec(open(r"D:\Dev\repos\kicad-mcp\src\kicad_mcp\kc_bridge.py").read())`

Server auto-detects bridge on port **11018**. See [docs/SETUP.md](docs/SETUP.md).

## Cursor MCP

See fleet doc `mcp-central-docs/projects/kicad-mcp/CURSOR_MCP.md` or snippet in `docs/NIGHTLY_HEADLESS.md`.
