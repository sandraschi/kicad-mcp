# Architecture

## High-Level Design

```
┌─────────────────────────────────────────────────────────────────┐
│                     kicad-mcp (port 11016)                       │
│                                                                  │
│  ┌──────────┐   ┌──────────────┐   ┌──────────────────────────┐ │
│  │  MCP     │   │   FastAPI    │   │     FastMCP Gateway      │ │
│  │  Client  │──▶│   REST API   │──▶│   (dual transport)       │ │
│  │  / LLM   │   │  /api/v1/*   │   │   @mcp.tool × 39        │ │
│  └──────────┘   └──────────────┘   └───────────┬──────────────┘ │
│                                                 │                │
│                       ┌─────────────────────────┼──────────┐     │
│                       ▼                         ▼          │     │
│  ┌──────────────────────────┐  ┌──────────────────────────┐  ┌──────────────────────────┐ │
│  │  Stable kicad-cli        │  │  IPC headless (11 nightly)│  │  TCP Bridge :11018       │ │
│  │  KICAD_CLI_PATH (10.x)   │  │  kicad-cli api-server     │  │  (KiCad 10 GUI legacy)   │ │
│  │  subprocess              │  │  kicad-python / kipy      │  │  kc_bridge.py SWIG       │ │
│  │                          │  │  CRUD: load, route, save  │  │  CRUD fallback           │ │
│  │  Export: STEP, Gerber,   │  │  No GUI required          │  │                          │ │
│  │  DRC/ERC, BOM, libraries │  │                           │  │                          │ │
│  └──────────────────────────┘  └──────────────────────────┘  └──────────────────────────┘ │
│                                                             │     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ┌──────────────────────────────┐
              │   frontend (port 11017)       │
              │   Vite + React 19 + Tailwind  │
              │   8 pages, Playwright e2e    │
              │   3D PCB viewer (GLB/Three.js)│
              └──────────────────────────────┘
```

## Module Dependency Graph

```
server.py
  ├── kicad_install.py     → hybrid CLI discovery (stable vs IPC nightly)
  ├── ipc_backend.py         → headless KiCad IPC session (kipy)
  ├── crud_router.py         → dispatch CRUD to IPC or TCP bridge
  ├── tools/pcb.py           → crud_send, run_kicad_cli
  ├── tools/schematic.py     → bridge_send, run_kicad_cli
  ├── tools/bom.py           → run_kicad_cli
  ├── tools/library.py       → run_kicad_cli
  ├── tools/marketplace.py   → run_kicad_cli, httpx
  └── kc_bridge.py           → pcbnew (TCP JSON-RPC server, legacy)
```

## CRUD backend selection

On startup (`server.py` lifespan):

1. Resolve **stable** CLI → export lane (`KICAD_CLI_PATH`, prefer 10.x without `api-server`).
2. Resolve **IPC** CLI → nightly with `kicad-cli api-server` (`KICAD_IPC_CLI_PATH`).
3. Probe TCP bridge on `KC_BRIDGE_PORT` (11018).
4. Set `crud_backend`: `ipc` (if IPC CLI + kipy) → else `tcp` → else `none`.

`KICAD_MCP_CRUD_BACKEND=auto|ipc|tcp|none` overrides auto pick. See [NIGHTLY_HEADLESS.md](./NIGHTLY_HEADLESS.md).

## Execution Mode Fallback

```python
if state["crud_backend"] in ("ipc", "tcp"):
    resp = await crud_send(method, params)
    if resp.get("success"):
        return resp
    if not resp.get("fallback"):
        return resp

# Export/read fallback to stable kicad-cli subprocess
result = await run_kicad_cli(args)
```

## State Management

Global `_state: dict` in `server.py` tracks:
- `crud_backend` / `bridge_mode`: `ipc`, `tcp`, or `none`
- `kicad_ok`: whether stable kicad-cli is found
- `kicad_cli_path`, `kicad_version` — export lane
- `kicad_ipc_cli_path`, `kicad_ipc_version`, `ipc_api_server`, `ipc_python_installed`
- `pcb_loaded` / `sch_loaded`: last loaded file paths

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| FastMCP 3.2 + FastAPI dual transport | MCP for LLM clients, REST for webapp |
| Hybrid stable + nightly KiCad | Fab-trusted 10.x exports + 11 nightly headless CRUD |
| IPC headless via kicad-python | No GUI; replaces SWIG bridge on 11 nightlies |
| TCP bridge for legacy pcbnew ops | Fallback when nightly not installed |
| kicad-cli fallback for read/export ops | Works headless on stable lane |
| Per-module `register_*_tools()` | Clean separation of concerns, easy to extend |
| `_READ_ONLY` / `_MUTATING` constants | SOTA MCP annotations for tool safety level |
| S-expression parsing for missing parts | Bridge not available, kicad-cli can't detect missing footprints |
