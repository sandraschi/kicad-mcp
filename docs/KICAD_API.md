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

## 3. IPC API (kicad-python) — kicad-mcp CRUD lane (v0.3.0+)

KiCad 9+ provides an IPC-based Python API via the `kicad-python` PyPI package.
kicad-mcp uses it for **headless PCB CRUD** when KiCad 11 nightly and `api-server` are available.

Install in kicad-mcp:

```powershell
uv sync --extra ipc
```

Hybrid env (see [NIGHTLY_HEADLESS.md](./NIGHTLY_HEADLESS.md)):

| Variable | Role |
|----------|------|
| `KICAD_CLI_PATH` | Stable 10.x — exports, DRC, ERC (unchanged) |
| `KICAD_IPC_CLI_PATH` | 11 nightly — spawns headless `api-server` |
| `KICAD_MCP_CRUD_BACKEND` | `auto` picks IPC → TCP → none |

```python
from kipy import KiCad

# kicad-mcp wraps this in ipc_backend.IpcHeadlessBackend
kicad = KiCad(headless=True, kicad_cli_path=r"C:\Program Files\KiCad\11.0\bin\kicad-cli.exe")
kicad.ping()
board = kicad.get_board()
```

| Feature | kicad-mcp v0.3.0 | Min KiCad |
|---------|:----------------:|:---------:|
| Board read (footprints, tracks, nets) | ✅ IPC headless | 11 nightly |
| Track/via CRUD | ✅ IPC headless | 11 nightly |
| Save board | ✅ IPC headless | 11 nightly |
| Footprint placement | ⚠️ TCP bridge only | — |
| Zone operations | ❌ not wired | 9.0+ IPC |
| Schematic support | ❌ export CLI only | TBD |
| Headless (`kicad-cli api-server`) | ✅ wired | 11 nightly |

Legacy GUI path: `kc_bridge.py` on TCP port 11018 (KiCad 10 SWIG) remains fallback until 11.0 stable.

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

## 7. KiCad vs Professional EDA Tools

KiCad is not a toy. It's used by CERN for particle accelerator electronics,
by Raspberry Pi for the Pico, and by Arduino for their reference designs.
Here's the honest comparison:

| Capability | KiCad (Free) | Altium ($8k/yr) | Cadence Allegro ($20k/yr) |
|------------|:------------:|:----------------:|:-------------------------:|
| Copper layers | 32 | Unlimited | Unlimited |
| Board size | Unlimited | Unlimited | Unlimited |
| Hierarchical schematics | ✅ | ✅ | ✅ |
| Push-and-shove routing | ✅ | ✅ | ✅ |
| Differential pairs | ✅ | ✅ | ✅ |
| Length tuning | ✅ manual | ✅ auto | ✅ auto |
| BGA fanout | ✅ manual | ✅ auto | ✅ auto |
| Impedance-controlled routing | ✅ | ✅ | ✅ |
| 3D viewer | ✅ STEP/GLB | ✅ | ✅ |
| Gerber/ODB++/IPC-2581 | ✅ all | ✅ | ✅ |
| Python scripting | ✅ deep pcbnew API | ✅ limited | ✅ SKILL |
| Simulation (SPICE) | ❌ external | ✅ built-in | ✅ |
| Signal integrity | ❌ | ✅ | ✅ HyperLynx |
| Thermal analysis | ❌ | ❌ | ✅ Celsius |
| ECAD-MCAD co-design | ❌ | ✅ | ✅ |
| Supply chain / distributor links | ❌ | ✅ Octopart | ❌ |
| Team collaboration | ❌ | ✅ Altium 365 | ✅ |
| Multi-board design | ❌ | ✅ | ✅ |
| **Price** | **Free** | **$8,000/yr** | **$20,000/yr** |

**The verdict**: KiCad does ~90% of what Altium does. The missing 10% is:
simulation integration, signal integrity analysis, and workflow polish
(multi-board, team collab, supply chain). For the 90% of PCB designs
that don't need these — including PC motherboards, consumer electronics,
and complex multi-layer boards — KiCad is production-ready.

**Why KiCad wins for MCP**: kicad-cli is unique. No other EDA tool has
a comprehensive headless CLI. Altium has no scripting CLI. Allegro has
SKILL but it requires a license. KiCad's `kicad-cli` + pcbnew Python
API make it the only EDA tool that can be fully driven by an LLM.

## 8. KiCad Plugin Ecosystem

See [KICAD_PLUGINS.md](KICAD_PLUGINS.md) for the full catalog of:
- PCM (Plugin and Content Manager) — built-in package manager
- Official plugins (Interactive BOM, Fabrication Toolkit, StepUp)
- Third-party plugins (KiBot, KiKit, KiCost, InteractiveHtmlBom, KiField)
- Helper apps and CLI tools
- Writing custom Action Plugins (SWIG) and IPC Plugins (KiCad 9+)
