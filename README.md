# KiCad MCP

KiCad PCB/schematic design automation via FastMCP 3.2 Unified Gateway.

AI-driven electronics design: component inspection, DRC/ERC analysis,
BOM generation, manufacturing export (STEP/Gerber), and cross-tool
pipeline with freecad-mcp for enclosure design.

## Quick Start

```powershell
just bootstrap
just serve
```

Then open http://localhost:11017 for the webapp.

## Prerequisites

- Python 3.12+ with uv
- KiCad 8.0+ (provides kicad-cli and pcbnew Python API)
- Node.js 20+ (for webapp)

## Architecture

```
MCP Client → HTTP/SSE → server.py → kicad-cli (headless CLI)
                                   → kc_bridge.py (GUI-dependent, internal to KiCad)
                                       ↓
                                   JSON response
```

## Tools

| Category | Tools |
|----------|-------|
| **PCB** | pcb_load, pcb_info, pcb_list_components, pcb_list_nets, pcb_list_tracks, pcb_get_component, pcb_drc, pcb_export_step, pcb_export_gerber, pcb_export_pos, pcb_export_dxf, pcb_export_svg, pcb_export_pdf, pcb_export_vrml, pcb_export_glb, pcb_export_ipc2581, pcb_export_odbpp, pcb_place_component, pcb_add_track, pcb_add_via, pcb_save, pcb_set_board_outline |
| **Schematic** | sch_load, sch_info, sch_erc, sch_export_netlist, sch_export_python_bom, sch_export_pdf, sch_export_svg, sch_export_dxf |
| **BOM** | bom_generate |
| **Library** | lib_list_footprints, lib_list_symbols, lib_find_footprint, lib_find_symbol, fp_export_svg, sym_export_svg |
| **Marketplace** | marketplace_search, marketplace_categories, marketplace_download, parts_search, parts_missing |
| **System** | kicad_status, kicad_supported_commands |

## Ports

- **11016**: Backend (FastAPI + FastMCP HTTP/SSE)
- **11017**: Frontend (Vite dev server)
- **11018**: KiCad TCP bridge (internal)
