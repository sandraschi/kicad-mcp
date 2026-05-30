# KiCad MCP

[![MIT License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue.svg)](pyproject.toml)
[![KiCad 10+ / 11 nightly IPC](https://img.shields.io/badge/KiCad-hybrid%2010%2B%2F11-orange.svg)](docs/NIGHTLY_HEADLESS.md)
[![GitHub last commit](https://img.shields.io/github/last-commit/sandraschi/kicad-mcp)](https://github.com/sandraschi/kicad-mcp)

AI-driven PCB/schematic design automation via **FastMCP 3.2**.
39 MCP tools across 6 categories — component inspection, DRC/ERC, BOM generation,
manufacturing export (Gerber, STEP, IPC-2581, ODB++), 3D visualization (GLB, VRML),
pick-and-place, library search, marketplace (GitHub/Kitspace/SnapEDA), and **live PCB
board editing** (place components, route tracks, add vias, set board outline, save).

## How it runs

| Mode | Host app | When |
|------|----------|------|
| **Export lane (default)** | Stable `kicad-cli` (KiCad 10.x), no pcbnew window | Gerber, STEP, GLB, DRC/ERC, BOM, schematic exports, library CLI |
| **Headless CRUD** | KiCad 11 nightly `kicad-cli api-server` + `kicad-python` | Load/save board, tracks, vias — no GUI |
| **Legacy TCP CRUD (optional)** | KiCad 10 GUI + `kc_bridge.py` on port 11018 | Fallback when nightly IPC unavailable; footprint placement |
| **Export-only** | Stable CLI only | CRUD tools return guidance if no IPC/TCP backend |

**You do not need to open KiCad’s pcbnew window** for exports, DRC, Gerber, or STEP — the server calls stable `kicad-cli` subprocesses automatically. PCB editing uses either headless IPC (11 nightly) or the legacy GUI bridge.

Install [KiCad](https://www.kicad.org/download/) separately (hybrid 10.x + optional 11 nightly); it is never bundled. Full setup: [docs/NIGHTLY_HEADLESS.md](docs/NIGHTLY_HEADLESS.md).

> **Headless by default for manufacturing** — DRC, Gerber, STEP, and BOM run on stable `KICAD_CLI_PATH` with no GUI. CRUD picks `ipc` → `tcp` → `none` at startup (`KICAD_MCP_CRUD_BACKEND=auto|ipc|tcp|none`). Probe: `uv run python -m kicad_mcp.scripts.probe_ipc_headless`.

```powershell
uv sync --extra ipc
uv run python -m kicad_mcp.scripts.probe_ipc_headless
```

## Hands-in / Hands-out

| Direction | Artifacts | Notes |
|-----------|-----------|-------|
| **Hands-in** | `.kicad_pcb`, `.kicad_sch` | Webapp upload or `pcb_load` / `sch_load` — copies land in `%TEMP%\kicad_mcp_work\uploads\` |
| **Hands-in** | Footprint/symbol refs, net names | Tool params; marketplace downloads via `marketplace_*` |
| **Hands-out** | Gerber, ODB++, IPC-2581, pick-and-place CSV | `pcb_export_*` — **headless** (stable CLI) |
| **Hands-out** | STEP, GLB, VRML, DXF, SVG, PDF | 3D/mechanical handoff — **headless** |
| **Hands-out** | DRC/ERC JSON, grouped BOM (JSON/CSV) | `pcb_drc`, `sch_erc`, `bom_generate` — **headless** |
| **Hands-out** | Modified `.kicad_pcb` | `pcb_save` after CRUD — IPC headless or TCP bridge |

### Fleet pipelines (downstream)

| Downstream MCP | Takes from kicad-mcp |
|----------------|----------------------|
| [freecad-mcp](https://github.com/sandraschi/freecad-mcp) | STEP board / enclosure models |
| [chip-design-mcp](https://github.com/sandraschi/chip-design-mcp) | Netlists, BOM, layout metadata |
| Fabrication | Gerber, ODB++, IPC-2581, POS files |

## Quick Start

```powershell
just bootstrap
just serve
# Open http://localhost:11017
```

## Table of Contents

- [How it runs](#how-it-runs) · [Hands-in / Hands-out](#hands-in--hands-out)
- [Setup & Configuration](docs/SETUP.md)
- [Tool Catalog (all 39 tools)](docs/TOOLS.md)
- [REST + MCP API Reference](docs/API.md)
- [Architecture Deep-Dive](docs/ARCHITECTURE.md)
- [Hybrid nightly + headless IPC](docs/NIGHTLY_HEADLESS.md) — KiCad 10 stable exports + 11 nightly CRUD
- [KiCad Scripting & API Reference](docs/KICAD_API.md)
- [KiCad Plugin Ecosystem](docs/KICAD_PLUGINS.md)
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

## KiCad vs Professional EDA Tools

KiCad is **production-grade**, used by CERN and Raspberry Pi. It covers ~90%
of Altium Designer's capability at zero cost.

| Capability | KiCad (Free) | Altium ($8k/yr) | Allegro ($20k/yr) |
|------------|:------------:|:----------------:|:-----------------:|
| Multi-layer PCB | ✅ 32 layers | ✅ | ✅ |
| Push-and-shove routing | ✅ | ✅ | ✅ |
| Differential pairs | ✅ | ✅ | ✅ |
| Length tuning | ✅ manual | ✅ auto | ✅ auto |
| 3D viewer | ✅ STEP/GLB | ✅ | ✅ |
| Gerber/ODB++/IPC-2581 | ✅ | ✅ | ✅ |
| Python scripting | ✅ deep pcbnew | ✅ limited | ✅ SKILL |
| **Price** | **Free** | **$8,000/yr** | **$20,000/yr** |

**Why KiCad wins for MCP**: No other EDA tool has `kicad-cli`. Altium
has no headless CLI. Allegro's SKILL needs a license. KiCad is the
**only** EDA tool that can be fully driven by an LLM.

See [docs/KICAD_API.md](docs/KICAD_API.md) for the full comparison.

## Plugin Ecosystem

KiCad has a rich plugin system (PCM, Action Plugins, IPC Plugins) and
a wide third-party ecosystem: KiBot (CI/CD), KiKit (panelization),
InteractiveHtmlBom, KiCost, KiField, and more.

See [docs/KICAD_PLUGINS.md](docs/KICAD_PLUGINS.md) for the full catalog.

## Ports

| Port | Service |
|------|---------|
| 11016 | Backend (FastAPI + FastMCP) |
| 11017 | Frontend (Vite dev) |
| 11018 | KiCad TCP bridge (internal) |

## License

MIT © 2026 Sandra Schipal. See [LICENSE](LICENSE).
