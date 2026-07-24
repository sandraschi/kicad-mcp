# KiCad MCP

[![MIT License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue.svg)](pyproject.toml)
[![uv](https://img.shields.io/badge/package%20manager-uv-23232f.svg)](https://docs.astral.sh/uv/)
[![FastMCP 3.4](https://img.shields.io/badge/FastMCP-3.4%2B-0891b2.svg)](https://github.com/jlowin/fastmcp)

**AI assistant for KiCad EDA** — an MCP server that gives Claude (or any LLM) the tools to inspect, design, and manufacture PCBs through KiCad.

Think of it as a **co-pilot for PCB design**: Claude can run DRC checks, export Gerbers, search component libraries, place parts, route traces, and prepare fabrication files — all without you touching KiCad's GUI.

[Installation](INSTALL.md) · [How it works](docs/HOW_IT_WORKS.md) · [Tool catalog](docs/TOOLS.md) · [Architecture](docs/ARCHITECTURE.md) · [API reference](docs/API.md)

---

## Quick Start

```powershell
just bootstrap   # install dependencies
just serve       # start server on port 11016
# Open http://localhost:11017 for the web dashboard
```

Requires [KiCad](https://www.kicad.org/download/) installed separately (stable 10.x for exports, optional 11 nightly for live board editing).

---

## What can you do with it?

| You ask Claude... | What happens | GUI needed? |
|---|---|---|
| "Run DRC on my board" | `kicad-cli` runs headless, returns violations | ❌ |
| "Export Gerbers for JLCPCB" | Generates all Gerber + drill files, zips them | ❌ |
| "Find a SOIC-8 footprint" | Searches KiCad libraries, returns results | ❌ |
| "Generate a BOM" | Parses schematic, outputs CSV/JSON | ❌ |
| "Place a 0.1uF cap at 50mm, 30mm" | IPC headless modifies board file | ❌ |
| "Route a track between these pads" | IPC headless adds the track | ❌ |
| "What's on my schematic?" | Reads netlist, returns component list | ❌ |
| "Audit my board for DFM issues" | AI analyzes board, suggests fixes | ❌ |

**Most operations run headless.** The only time KiCad's GUI opens is if you use the legacy TCP bridge mode (fallback for older KiCad versions). See [How it works](docs/HOW_IT_WORKS.md#headless-vs-gui).

---

## The Schematic → Board Flow

KiCad design goes: **schematic → footprints → netlist → board layout → exports**

Each step has MCP tools to automate it:

| Step | What happens | Tool | Automated? |
|------|-------------|------|------------|
| 1. Draw schematic | Place symbols, wire connections | `sch_load`, manual in KiCad GUI | 🟡 Visual work |
| 2. Assign footprints | Match each symbol to a physical package | `lib_find_footprint` | ✅ |
| 3. Generate netlist | Create the connectivity map | `sch_export_netlist` | ✅ |
| 4. Place components | Position parts on the board | `pcb_place_component` | ✅ (need coordinates) |
| 5. Route traces | Connect the pads | `pcb_add_track` | ✅ (need coordinates) |
| 6. Verify | Run DRC/ERC | `pcb_drc`, `sch_erc` | ✅ |
| 7. Export | Generate manufacturing files | `pcb_export_gerber`, `pcb_export_step`, `bom_generate` | ✅ |

**The creative steps** (schematic capture, component placement strategy, routing topology) still benefit from the visual KiCad GUI. The MCP server handles **everything else** — verification, export, library search, and programmatic changes driven by Claude.

---

## Web Dashboard

A React + Three.js webapp provides a [board marketplace](docs/BOARD_MARKETPLACE.md) (browse & download KiCad projects from GitHub), 3D board viewer, AI chat (PCB design co-pilot), fabrication pipeline with order tracking, design review with annotations, and a parametric component browser. Access at `http://localhost:11017`.

---

## Why KiCad?

KiCad is the **only** EDA tool with a full headless CLI (`kicad-cli`). Altium, Allegro, and Eagle have no equivalent. This makes KiCad uniquely suited for AI-driven automation — Claude can control it without needing a display server or GUI license.

---

## Contents

| Document | What it covers |
|----------|---------------|
| [INSTALL.md](INSTALL.md) | Installing KiCad, dependencies, configuration |
| [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md) | Headless vs GUI, schematic→board flow, automation level |
| [docs/BOARD_MARKETPLACE.md](docs/BOARD_MARKETPLACE.md) | Browse and download KiCad projects from GitHub |
| [docs/TOOLS.md](docs/TOOLS.md) | All 41 MCP tools by category |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Code structure, IPC vs TCP, lifespan |
| [docs/API.md](docs/API.md) | REST + MCP API reference |
| [docs/NIGHTLY_HEADLESS.md](docs/NIGHTLY_HEADLESS.md) | Setting up KiCad 11 nightly for headless IPC |
| [docs/KICAD_API.md](docs/KICAD_API.md) | KiCad scripting comparison |

## License

MIT © 2026 Sandra Schipal
