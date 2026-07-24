# KiCad MCP — PCB Design Skill

## Overview

KiCad MCP provides 41 MCP tools for automated PCB and schematic design. Use this skill when designing, inspecting, or manufacturing printed circuit boards.

## Tool Categories

| Category | Tools | Description |
|----------|-------|-------------|
| **PCB** | 21 | Load, info, DRC, export (Gerber/STEP/PDF/SVG), place components, add tracks/vias |
| **Schematic** | 8 | Load, info, ERC, export netlist/PDF/SVG |
| **BOM** | 1 | Generate bill of materials |
| **Library** | 6 | Search footprints and symbols, export SVG |
| **Marketplace** | 5 | Search and download from GitHub/SnapEDA/kitspace |
| **System** | 2 | KiCad status, supported commands |

## Design Workflow

### 1. Setup & Inspection
- `kicad_status()` — check available backends and versions
- `pcb_info(file_name)` — inspect board metadata
- `sch_info(file_name)` — inspect schematic
- `pcb_drc(file_name)` — run design rule check

### 2. Schematic Design
- `sch_load(file_name)` — load schematic
- `sch_erc(file_name)` — run electrical rules check
- `sch_export_netlist(file_name)` — export to netlist
- `sch_export_pdf(file_name)` — export schematic PDF

### 3. PCB Layout
- `pcb_load(file_name)` — load PCB
- `pcb_place_component(library, footprint, reference, x_mm, y_mm, rotation_deg)` — place a part
- `pcb_add_track(start_x_mm, start_y_mm, end_x_mm, end_y_mm, layer, width_mm)` — route a track
- `pcb_add_via(x_mm, y_mm, diameter_mm, drill_mm)` — add a via
- `pcb_save()` — save changes

### 4. Export for Manufacturing
- `pcb_drc(file_name)` — verify design rules
- `pcb_export_gerber(file_name)` — generate Gerber files
- `pcb_export_step(file_name)` — generate 3D model
- `pcb_export_pdf(file_name)` — generate fabrication drawing
- `bom_generate(file_name)` — generate BOM

## Example Sequences

**Place a decoupling capacitor near an IC:**
```
1. lib_find_footprint(query="C_0805") — find capacitor footprint
2. pcb_place_component(library="Capacitor_SMD", footprint="C_0805", reference="C1", value="0.1uF", x_mm=50, y_mm=30)
3. pcb_add_track(start_x_mm=50, start_y_mm=30, end_x_mm=50, end_y_mm=20, layer="F.Cu", width_mm=0.25)
```

**Export boards for JLCPCB fabrication:**
```
1. pcb_drc(file_name="design.kicad_pcb") — pass DRC first
2. pcb_export_gerber(file_name="design.kicad_pcb") — generate Gerber
3. pcb_export_pos(file_name="design.kicad_pcb") — generate pick-and-place
4. GET /api/v1/fab/export — zip and prepare for ordering
```

## Notes

- Use copies of boards in %TEMP%\kicad_mcp_work\uploads\ for CRUD experiments
- DRC and manufacturing exports always use stable kicad-cli (KICAD_CLI_PATH), not IPC
- KiCad 11 nightly allows headless IPC for CRUD; KiCad 10.x supports export only
