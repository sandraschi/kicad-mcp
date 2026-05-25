# KiCad MCP

[![MIT License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue.svg)](pyproject.toml)
[![KiCad 8+](https://img.shields.io/badge/KiCad-8%2B-orange.svg)](https://www.kicad.org)
[![MCP Server](https://img.shields.io/badge/MCP%20Server-glama.ai-blue)](https://glama.ai/mcp/servers/...)
[![smithery](https://img.shields.io/badge/dynamic/json?url=https://smithery.ai/api/v1/servers/kicad-mcp&query=downloads&label=Smithery)](https://smithery.ai/server/kicad-mcp)
[![GitHub last commit](https://img.shields.io/github/last-commit/sandraschi/kicad-mcp)](https://github.com/sandraschi/kicad-mcp)

AI-driven PCB/schematic design automation via **FastMCP 3.2**.
39 MCP tools across 6 categories — component inspection, DRC/ERC, BOM generation,
manufacturing export (Gerber, STEP, IPC-2581, ODB++), 3D visualization (GLB, VRML),
pick-and-place, library search, marketplace (GitHub/Kitspace/SnapEDA), and **live PCB
board editing** (place components, route tracks, add vias, set board outline, save).

## Quick Start

```powershell
just bootstrap
just serve
# Open http://localhost:11017
```

## Badges

| | |
|---|---|
| [Glama MCP Server](https://glama.ai/mcp/servers/...) | ![MCP Server](https://img.shields.io/badge/MCP%20Server-glama.ai-blue) |
| Install via Smithery | `npx @smithery/cli install kicad-mcp` |

## Table of Contents

- [Setup & Configuration](docs/SETUP.md)
- [Tool Catalog (all 39 tools)](docs/TOOLS.md)
- [REST + MCP API Reference](docs/API.md)
- [Architecture Deep-Dive](docs/ARCHITECTURE.md)
- [KiCad Scripting Reference](docs/KICAD_API.md)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

## Tools Overview

| Category | Count | Tools |
|----------|-------|-------|
| **PCB** | 17 | load, info, inspect, DRC, export (STEP/Gerber/POS/DXF/SVG/PDF/VRML/GLB/IPC-2581/ODB++), place component, add track/via, save, set board outline |
| **Schematic** | 8 | load, info, ERC, export (netlist/BOM/PDF/SVG/DXF) |
| **BOM** | 1 | generate (grouped JSON/CSV) |
| **Library** | 6 | list/search footprints/symbols, export SVG |
| **Marketplace** | 5 | search (GitHub/Kitspace/SnapEDA), download, find parts |
| **System** | 2 | status, supported commands |

## KiCad Integration

Three execution modes:

1. **kicad-cli** — headless, always available if KiCad installed
2. **TCP bridge** (`kc_bridge.py`) — pcbnew BOARD CRUD (requires KiCad GUI)
3. **IPC API** (upcoming) — kicad-python for KiCad 9+ headless mode

## Ports

| Port | Service |
|------|---------|
| 11016 | Backend (FastAPI + FastMCP) |
| 11017 | Frontend (Vite dev) |
| 11018 | KiCad TCP bridge (internal) |

## License

MIT © 2026 Sandra Schipal. See [LICENSE](LICENSE).
