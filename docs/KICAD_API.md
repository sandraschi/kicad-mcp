# KiCad Scripting & API Reference

This document catalogs KiCad's programmatic interfaces relevant to kicad-mcp.

## 1. kicad-cli (All Versions)

The headless command-line interface. Always available if KiCad is installed.

### PCB Commands

```
pcb drc                — Design Rule Check (report/JSON, severity filtering)
pcb export step        — STEP 3D model (tracks, zones, pads, silkscreen, soldermask)
pcb export gerbers     — Gerber per layer
pcb export drill       — Excellon drill files (separate TH/NPTH, map)
pcb export pos         — Pick-and-place (ASCII, CSV, Gerber; side filtering)
pcb export dxf         — DXF (single or multi-layer)
pcb export svg         — SVG per layer
pcb export pdf         — PDF (single, separate, multi-page)
pcb export vrml        — VRML 3D model
pcb export glb         — GLB (binary glTF) 3D model
pcb export ipc2581     — IPC-2581 (Rev B or C)
pcb export odb         — ODB++ (KiCad 9+, ZIP/TGZ compress)
pcb info               — Board metadata JSON
pcb render             — Headless rendering (KiCad 9+)
```

### Schematic Commands

```
sch erc                — Electrical Rules Check (report/JSON)
sch export netlist     — Netlist (kicadsexpr, kicadxml, cadstar, orcadpcb2, spice)
sch export bom         — Structured BOM (fields, grouping, presets)
sch export python-bom  — Legacy XML BOM
sch export pdf         — PDF (multi-page, theme, property popups)
sch export svg         — SVG per sheet
sch export dxf         — DXF per sheet
sch info               — Schematic metadata JSON
```

### Footprint & Symbol Commands

```
fp export svg          — Footprint SVG (single or library)
fp upgrade             — Migrate legacy libraries (KiCad 9+ supports Altium, EAGLE, EasyEDA, GEDA)
sym export svg         — Symbol SVG
sym upgrade            — Migrate legacy symbol libraries
```

### Automation (KiCad 9+)

```
jobset run             — Execute .kicad_jobset pipeline
```

## 2. pcbnew Python SWIG (Deprecated — Removed in KiCad 11)

Available inside KiCad's Python console or as `import pcbnew` if KiCad's Python libs are on sys.path.

### Key Classes

| Class | Purpose |
|-------|---------|
| `BOARD` | Root board object. LoadBoard(), SaveBoard(), GetFootprints(), GetTracks() |
| `FOOTPRINT` | Component. GetReference(), SetPosition(), GetValue(), Pads() |
| `PAD` | Pad within footprint. GetPosition(), GetNet(), GetSize(), GetDrillSize() |
| `PCB_TRACK` | Track segment. SetStart(), SetEnd(), SetWidth(), SetLayer() |
| `PCB_VIA` | Via. SetPosition(), SetWidth(), SetDrill(), SetViaType() |
| `PCB_SHAPE` | Graphical shape. Used for board outline, text, dimensions |
| `ZONE` | Copper zone. GetPolyShape(), GetLayer(), GetFilledPolysList() |
| `NETINFO_ITEM` | Net. GetNetname(), GetNetCode(), Pads() |
| `DRC_ENGINE` | Design rule check engine |
| `PLOT_CONTROLLER` | Programmatic Gerber/PDF/SVG plotting |
| `PCB_IO` | Read/write board files. Load(), Save() |
| `EXCELLON_WRITER` | Drill file generation |
| `PLACE_FILE_EXPORTER` | Pick-and-place generation |

### CRUD via pcbnew

```python
import pcbnew

# Read
board = pcbnew.LoadBoard("board.kicad_pcb")
for fp in board.GetFootprints():
    print(fp.GetReference(), fp.GetPosition())

# Create — footprint
fp = pcbnew.FootprintLoad("Resistor_SMD", "R_US_0603")
fp.SetReference("R1")
fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(50), pcbnew.FromMM(30)))
board.Add(fp)

# Create — track
track = pcbnew.PCB_TRACK(board)
track.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(0), pcbnew.FromMM(0)))
track.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(10), pcbnew.FromMM(10)))
board.Add(track)

# Create — via
via = pcbnew.PCB_VIA(board)
via.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(5), pcbnew.FromMM(5)))
board.Add(via)

# Update
fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(60), pcbnew.FromMM(30)))

# Delete
board.Remove(track)

# Save
pcbnew.SaveBoard("board_v2.kicad_pcb", board)
```

## 3. IPC API (kicad-python) — Recommended Future Path

KiCad 9+ introduces a new IPC-based Python API via the `kicad-python` PyPI package.
This replaces SWIG and works outside the KiCad process (via named pipes / Unix sockets).

```bash
pip install kicad-python
```

```python
from kipy import KiCad

kicad = KiCad()
project = kicad.open_project("path/to/project")
board = project.board

for fp in board.footprints:
    print(fp.reference, fp.position)

# Create footprint
from kipy.board_types import Footprint, Vector2
fp = Footprint()
fp.reference = "R1"
fp.position = Vector2.from_mm(10, 10)
board.add(fp)
board.commit()
```

| Feature | Status | Min KiCad |
|---------|--------|-----------|
| Board read (footprints, tracks, nets, zones) | Stable | 9.0 |
| Board write (add/remove/modify items) | Stable | 9.0 |
| Footprint placement | Stable | 9.0 |
| Track/via CRUD | Stable | 9.0 |
| Zone operations | Stable | 9.0 |
| Pad/padstack editing | Stable | 9.0 |
| Schematic support | Upcoming | TBD |
| Headless (`kicad-cli api-server`) | Upcoming | 11.0 |

## 4. Plugin System

### Action Plugins (Legacy, removed in KiCad 11)

```python
import pcbnew

class MyPlugin(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "My Plugin"
        self.description = "Does something"

    def Run(self):
        board = pcbnew.GetBoard()
        # ...
```

### IPC Plugins (Modern, KiCad 9+)

Plugin directory: `%USERPROFILE%/Documents/KiCad/<version>/plugins`

Uses `plugin.json` metadata:
```json
{
    "name": "My Plugin",
    "type": "ipc",
    "actions": [{"name": "my_action", "label": "My Action"}]
}
```

## 5. Schematic Scripting Limitations

**Important**: KiCad currently has **no Python API for schematics**:
- No SWIG module for eeschema
- IPC API schematic support is "upcoming" (not yet released)
- The only way to programmatically modify `.kicad_sch` files is:
  1. S-expression file parsing (`.kicad_sch` is plain text)
  2. kicad-cli export (read-only: PDF, SVG, DXF, netlist, BOM, ERC)
  3. GUI automation via scripting console

## 6. KiCad Version Comparison

| Feature | 8.0 | 9.0 | 10.0 | 11.0 |
|---------|:---:|:---:|:----:|:----:|
| kicad-cli | ✅ | ✅ | ✅ | ✅ |
| pcbnew SWIG | ✅ | ✅ (deprecated) | ✅ (deprecated) | ❌ removed |
| IPC API (kicad-python) | ❌ | ✅ | ✅ | ✅ |
| Headless IPC | ❌ | ❌ | ❌ | ✅ (api-server) |
| Schematic SWIG | ❌ | ❌ | ❌ | ❌ |
| ODB++, STL, PLY, BREP, render | ❌ | ✅ | ✅ | ✅ |
| Jobset automation | ❌ | ✅ | ✅ | ✅ |
