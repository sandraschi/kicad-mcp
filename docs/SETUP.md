# Setup & Configuration

## Prerequisites

- Python 3.12+ with [uv](https://docs.astral.sh/uv/)
- KiCad 8.0+ (provides `kicad-cli` and `pcbnew` Python API)
- Node.js 20+ (for webapp)

## Quick Install

```powershell
git clone https://github.com/sandraschi/kicad-mcp.git
cd kicad-mcp
just bootstrap
just serve
```

Opens at http://localhost:11017.

## Manual Steps

### 1. Python bootstrap

```powershell
uv sync --all-extras
```

### 2. Webapp bootstrap

```powershell
cd webapp
npm install
cd ..
```

### 3. Start backend

```powershell
uv run python -m kicad_mcp.server --mode dual --port 11016
```

### 4. Start frontend

```powershell
npx --prefix webapp vite --port 11017
```

### 5. TCP Bridge (for board editing)

To enable PCB CRUD (place components, route tracks, add vias), run `kc_bridge.py` inside KiCad:

1. Open KiCad
2. Tools → Scripting Console
3. Open `src/kicad_mcp/kc_bridge.py`
4. Run it

Or launch KiCad with the bridge:

```powershell
kicad --script=src/kicad_mcp/kc_bridge.py
```

## Windows Binary (Tauri)

See [native/README.md](../native/README.md) for building a standalone desktop installer.

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `KICAD_CLI_PATH` | auto-detect | Path to kicad-cli.exe |
| `KC_BRIDGE_PORT` | 11018 | TCP port for KiCad bridge |
| `KICAD_MCP_WORK_DIR` | `%TEMP%\kicad_mcp_work` | Upload/output directory |
| `GITHUB_TOKEN` | — | For marketplace GitHub API (higher rate limit) |
| `SNAPEDA_API_KEY` | — | For marketplace SnapEDA component downloads |
