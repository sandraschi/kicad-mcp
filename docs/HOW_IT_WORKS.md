# How KiCad MCP Works

If you're new to PCB design or KiCad, this doc explains what this server does, when it opens KiCad's GUI, and what you can realistically automate.

---

## What is KiCad?

[KiCad](https://www.kicad.org/) is a free, open-source EDA (Electronic Design Automation) tool for designing printed circuit boards. It has a GUI where you draw schematics and lay out boards — much like a vector drawing program, but with electrical-awareness (nets, footprints, design rules).

KiCad also ships `kicad-cli`, a command-line tool that can do most operations **without opening the GUI**. This is rare — Altium, Eagle, and Allegro don't have this. That's the whole reason this MCP server exists: `kicad-cli` gives Claude a way to interact with board designs programmatically.

---

## Headless vs GUI

| Mode | What runs | KiCad GUI opens? | When to use |
|------|-----------|-------------------|-------------|
| **Export lane** (default) | `kicad-cli` subprocess | ❌ No | DRC, ERC, Gerber/STEP/PDF export, BOM, library search |
| **IPC headless** (KiCad 11 nightly) | `kicad-cli api-server` + `kicad-python` | ❌ No | Load/save boards, place parts, route tracks, add vias |
| **TCP bridge** (KiCad 10 legacy) | `kc_bridge.py` via TCP | ✅ Yes, pcbnew window | Fallback when nightly IPC isn't available |

**Most operations never open KiCad.** The only time KiCad's GUI appears is if you're using the legacy TCP bridge mode (KiCad 10.x with pcbnew running), and even then it's a background window — Claude drives it via TCP commands, not by clicking buttons.

### Is headless KiCad actually useful?

Yes — but not for everything. Here's the honest breakdown:

**Fully useful headless:**
- ✅ Running DRC (design rule check) — detects clearance violations, unconnected nets
- ✅ Running ERC (electrical rules check) — catches shorted outputs, unconnected pins
- ✅ Exporting Gerber files for manufacturing
- ✅ Generating STEP/3D models for mechanical CAD
- ✅ Creating BOM (bill of materials)
- ✅ Searching libraries for footprints and symbols
- ✅ Generating fabrication drawings (PDF, SVG, DXF)
- ✅ Batch operations across many files

**Partially useful headless:**
- 🟡 Placing components — works if you know exact coordinates, but you can't SEE the board. The web dashboard's 3D viewer helps here.
- 🟡 Routing traces — same: the tools exist, you just need spatial awareness. Claude can place tracks, but routing a complex board "blind" is impractical. Use the 3D dashboard to verify.

**Not useful headless:**
- ❌ Schematic capture — drawing circuits is inherently visual. Claude can help with component selection and BOM, but creating a schematic from scratch needs the KiCad GUI.
- ❌ Creative component placement — deciding WHERE to put a decoupling capacitor relative to an IC requires visual judgment. Claude can place it, but you should verify in the GUI.

**Bottom line:** KiCad MCP excels at **verification, export, library search, and programmatic edits**. For creative design work, you pair it with the KiCad GUI — Claude handles the tedious parts.

---

## The Schematic → Board Flow

PCB design follows a well-defined pipeline. Here's exactly how it works and what each step means:

### Step 1: Schematic Capture

**What happens:** You draw the circuit — place symbols (resistors, ICs, connectors) and wire them together. KiCad calls this a "schematic" (`.kicad_sch` file).

**Claude can:** Load an existing schematic (`sch_load`), check it (`sch_info`, `sch_erc`), and export it.

**Need the GUI for:** The initial drawing — placing symbols and connecting them is visual work.

### Step 2: Assign Footprints

**What happens:** Each schematic symbol needs a physical "footprint" — the actual copper pattern on the PCB. An 0805 resistor has a different footprint than a through-hole resistor. KiCad stores these in libraries.

**Claude can:**
- `lib_find_footprint("SOIC-8")` — find the footprint for an SOIC-8 IC
- `lib_find_symbol("STM32F103")` — find the schematic symbol
- `fp_export_svg("SOIC-8")` — preview the footprint as SVG

**Automation level:** ✅ High — library search is entirely headless.

### Step 3: Generate Netlist

**What happens:** The netlist is the "connectivity map" — it lists every component pin and which net (signal) it connects to. KiCad's PCB editor imports this to know what needs to be routed.

**Claude can:** `sch_export_netlist("design.kicad_sch")` — generates the netlist file.

**Automation level:** ✅ Fully automated.

### Step 4: Board Layout (PCB)

**What happens:** The PCB editor imports the netlist. You place components on the board outline, then route copper tracks to connect the pins according to the netlist.

**Claude can:**
- `pcb_load("design.kicad_pcb")` — load the board
- `pcb_place_component(library="Resistor_SMD", footprint="R_0805", reference="R1", x_mm=50, y_mm=30, rotation_deg=0)` — place a part
- `pcb_add_track(start_x_mm=50, start_y_mm=30, end_x_mm=60, end_y_mm=30, layer="F.Cu", width_mm=0.25)` — route a track
- `pcb_add_via(x_mm=55, y_mm=30, diameter_mm=0.6, drill_mm=0.3)` — add a via
- `pcb_save()` — save the modified board

**Automation level:** 🟡 Works programmatically, but spatial layout is best done visually. Use the 3D dashboard viewer to inspect results.

### Step 5: Design Rule Check

**What happens:** DRC checks your board against manufacturing rules — minimum clearance, minimum track width, unconnected nets, drill-to-copper spacing, etc.

**Claude can:** `pcb_drc("design.kicad_pcb")` — returns all violations as structured data.

**Automation level:** ✅ Fully automated, and faster than running it in the GUI.

### Step 6: Export for Manufacturing

**What happens:** You generate Gerber files (copper layers, solder mask, silkscreen), drill files, and pick-and-place files. These go to a PCB fab house (JLCPCB, PCBWay, etc.).

**Claude can:**
- `pcb_export_gerber("design.kicad_pcb")` — generate Gerbers
- `pcb_export_step("design.kicad_pcb")` — generate 3D model
- `pcb_export_pos("design.kicad_pcb")` — pick-and-place file
- `bom_generate("design.kicad_pcb")` — bill of materials
- Zip and prepare for ordering via the Fab page

**Automation level:** ✅ Fully automated. The web dashboard's Fab page even tracks order history.

---

## Real-World Automation Examples

### "Every time I save, run DRC and email me violations"

Fully automatable via the MCP tools — Claude can watch for file changes, run DRC, and report.

### "Generate Gerbers for my current project"

Fully headless. One tool call: `pcb_export_gerber("project.kicad_pcb")`.

### "Place 10 resistors around the IC"

Works headless, but you need to provide coordinates. Better flow:
1. `pcb_info("board.kicad_pcb")` — get board dimensions
2. `pcb_place_component(...)` — place each resistor
3. View result in 3D dashboard
4. Adjust positions as needed

### "Review my board for manufacturing issues"

The design review page runs an AI audit that checks common DFM (Design for Manufacturing) rules — clearance, silkslap, via-in-pad, thermal relief, etc.

---

## Tools by Category

| Category | What they do |
|----------|-------------|
| **PCB** (21 tools) | Load boards, inspect, DRC, export (Gerber/STEP/PDF/SVG/GLB/ODB++/IPC-2581), place components, route tracks, add vias |
| **Schematic** (8 tools) | Load schematics, inspect, ERC, export netlist/PDF/SVG |
| **BOM** (1 tool) | Generate bill of materials |
| **Library** (6 tools) | Search footprints and symbols, export SVG previews |
| **Marketplace** (5 tools) | Search GitHub/Kitspace/SnapEDA, download parts |
| **System** (2 tools) | Check KiCad status, list supported commands |

Full reference: [TOOLS.md](TOOLS.md)

---

## Architecture Overview

```
LLM (Claude) → FastMCP → kicad-cli (stable exports/DRC)
                       → IPC headless (KiCad 11 nightly for CRUD)
                       → TCP bridge (KiCad 10 legacy GUI)
                       → JSON response
```

Three execution lanes, auto-selected at startup based on what's installed. The REST API and web dashboard talk to the same backend.

Detailed architecture: [ARCHITECTURE.md](ARCHITECTURE.md)
