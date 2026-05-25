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
│  ┌──────────────────────────┐  ┌──────────────────────────┐ │     │
│  │     kicad-cli            │  │  TCP Bridge :11018       │ │     │
│  │     subprocess           │  │  (KiCad GUI needed)      │ │     │
│  │     (headless)           │  │  pcbnew BOARD API        │ │     │
│  │                          │  │  CRUD: place, route, via │ │     │
│  │  Export: STEP, Gerber,   │  │  Save: persist to file   │ │     │
│  │  POS, DXF, SVG, PDF,     │  │                          │ │     │
│  │  VRML, GLB, IPC-2581,    │  │  Read: info, components, │ │     │
│  │  ODB++, netlist, BOM     │  │  nets, tracks, DRC       │ │     │
│  └──────────────────────────┘  └──────────────────────────┘ │     │
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
  ├── tools/pcb.py           → bridge_send, run_kicad_cli
  ├── tools/schematic.py     → bridge_send, run_kicad_cli
  ├── tools/bom.py           → run_kicad_cli
  ├── tools/library.py       → run_kicad_cli
  ├── tools/marketplace.py   → run_kicad_cli, httpx
  └── kc_bridge.py           → pcbnew (TCP JSON-RPC server)
```

## Execution Mode Fallback

```python
if state["bridge_mode"] == "tcp":
    resp = await bridge_send(method, params)
    if resp.get("success"):
        return resp
    if not resp.get("fallback"):
        return resp  # bridge error, don't fall back

# Fallback to kicad-cli subprocess
result = await run_kicad_cli(args)
```

## State Management

Global `_state: dict` in `server.py` tracks:
- `bridge_mode`: "tcp", "cli", or "none"
- `kicad_ok`: whether kicad-cli is found
- `pcb_loaded` / `sch_loaded`: last loaded file paths
- `kicad_cli_path`, `kicad_version`

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| FastMCP 3.2 + FastAPI dual transport | MCP for LLM clients, REST for webapp |
| TCP bridge for pcbnew ops | pcbnew SWIG only available inside KiCad process |
| kicad-cli fallback for read ops | Works headless, no GUI needed |
| Per-module `register_*_tools()` | Clean separation of concerns, easy to extend |
| `_READ_ONLY` / `_MUTATING` constants | SOTA MCP annotations for tool safety level |
| S-expression parsing for missing parts | Bridge not available, kicad-cli can't detect missing footprints |
