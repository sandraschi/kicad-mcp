# KiCad Plugin & Helper Ecosystem

This document catalogs the broader KiCad plugin/extension ecosystem.
Useful for understanding what kicad-mcp could integrate with.

## PCM (Plugin and Content Manager)

KiCad 7+ ships a built-in package manager. Access via Tools → Plugin
and Content Manager. It hosts both plugins and library packages.

Repository: `https://gitlab.com/kicad/libraries/kicad-packages3d`

## Official / Shipped Plugins

| Plugin | Description | Relevance to kicad-mcp |
|--------|-------------|----------------------|
| **Interactive BOM** | Web-based BOM viewer with component highlighting | Could replace `bom_generate` output with interactive UI |
| **Fabrication Toolkit** | Gerber/drill/pos export with ZIP packaging | kicad-cli already covers this |
| **KiCad StepUp** | FreeCAD ↔ KiCad IPC bridge | Direct pipeline: STEP export → enclosure |
| **PCB Calculator** | Track impedance, via current, RF tools | Could expose as MCP tools |
| **Drawing Sheet Editor** | Custom title blocks | Low priority |

## Third-Party Plugins

### Design & Layout

| Plugin | Description | Integration Potential |
|--------|-------------|---------------------|
| **KiBot** | Automated board assembly, testing, documentation | High — could be an MCP tool to run KiBot jobs |
| **KiKit** | Panelization, automatic PCB assembly | High — kicad-mcp could call panelization |
| **Diff-Pair Router** | Differential pair routing helpers | Medium — bridge already has pcb_add_track |
| **Netclass Tools** | Batch netclass assignment and rule setup | Medium |
| **KiField** | Batch component field editing in schematics | High — fills the no-schematic-API gap |
| **WireIt** | Cable harness documentation from netlists | Low |

### Manufacturing & Documentation

| Plugin | Description | Integration Potential |
|--------|-------------|---------------------|
| **InteractiveHtmlBom** | HTML BOM with component highlighting | Medium — could expose generated HTML |
| **KiCad to Fusion360** | STEP-based bridge to Fusion 360 | Low (freecad-mcp is the fleet standard) |
| **KiCost** | Cost estimation from BOM (DigiKey/Mouser/LCSC) | High — could wrap as MCP tool |
| **PCBWay Fabrication Toolkit** | Direct-to-fab export with automated checks | Medium |
| **KiCad to JLCPCB** | JLCPCB-specific Gerber + BOM + CPL export | Medium |

### Signal Integrity & Analysis

| Plugin | Description | Integration Potential |
|--------|-------------|---------------------|
| **KiCad SPICE simulators** | Ngspice integration (built-in) | Medium — could wrap simulation as MCP tool |
| **Qucs-S** | GUI + ngspice/Qucsator RF simulation | Low |
| **OpenEMS** | 3D EM field simulation integration | Low |
| **pyEDAr** | Python RF/microwave design automation | Low |
| **SAT (System Assembly Tool)** | ECAD ↔ MCAD assembly validation | Low |

### Library & Part Management

| Plugin | Description | Integration Potential |
|--------|-------------|---------------------|
| **KiPart** | Parametric part generator | Medium — could generate library parts on demand |
| **KiBuzzard** | Text and silkscreen tools | Low |
| **Teigha for KiCad** | DXF/DWG import for board outlines | Medium — could integrate with pcb_set_board_outline |

## Helper Applications & Tools

### CLI Tools (not plugins, standalone)

| Tool | Description | Relevance |
|------|-------------|-----------|
| **kicad-cli** | KiCad command-line interface | Core backend of kicad-mcp |
| **pcbnew (Python)** | Python module for BOARD manipulation | Current bridge backend |
| **kicad-python (kipy)** | IPC API PyPI package | Future headless CRUD backend |
| **KiBot** | CI/CD for KiCad projects | Could wrap as `pcb_run_kibot` |
| **KiKit** | Panelization CLI | Could wrap as `pcb_panelize` |
| **python-kicad** | Older third-party Python bindings | Not recommended (SWIG-based, unmaintained) |

### GUI Tools

| Tool | Description |
|------|-------------|
| **KiCad** | The main EDA suite (eeschema + pcbnew) |
| **FreeCAD** | Mechanical CAD with KiCad StepUp bridge |
| **ViewPlot** | Gerber viewer (standalone) |
| **Gerbv / Gerblook** | Online Gerber viewers |
| **Travis CI for KiCad** | Automated DRC on commits (historical; now GitHub Actions) |

## Fleet-Preferred Integration Paths

For the fleet architecture, the most valuable integrations are:

### High Priority
1. **KiCAD + freecad-mcp** — `pcb_export_step` → `freecad-mcp import_step`
   → enclosure design. Already works.
2. **KiCAD + godot-mcp** — `pcb_export_glb` → interactive 3D board viewer.
   Already works (Three.js in webapp).

### Medium Priority
3. **KiBot integration** — Run KiBot automation jobs from MCP tools.
   KiBot can generate testing fixtures, panelization, assembly docs.
4. **KiCost integration** — BOM → cost estimation from distributors.
   `bom_generate` feeds into KiCost.
5. **Kitspace / Hackaday integration** — Publish completed designs.

### Future
6. **JLCPCB/PCBWay direct order** — Gerber + BOM + POS → order API.
   Would make kicad-mcp a full design-to-fab pipeline.

## Creating Custom KiCad Action Plugins

KiCad plugins live in:
- `%APPDATA%/kicad/<version>/scripting/plugins/` (Windows)
- `~/.local/share/kicad/<version>/scripting/plugins/` (Linux)

### SWIG Action Plugin (deprecated, removed in KiCad 11)

```python
import pcbnew

class MyPlugin(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "My Plugin"
        self.description = "Does something useful"
        self.show_toolbar_button = True

    def Run(self):
        board = pcbnew.GetBoard()
        # ... do something
```

### IPC Plugin (KiCad 9+, modern)

Uses `plugin.json` + Python script:
```json
{
    "name": "my-plugin",
    "type": "ipc",
    "actions": [
        {"name": "my_action", "label": "My Action", "tooltip": "Does something"}
    ]
}
```

Plugin directory: `%USERPROFILE%/Documents/KiCad/<version>/plugins/`

## Reference: Awesome KiCad

The curated Awesome KiCad list lives at:
`https://github.com/INTI-CMNB/KiCadAwesome`

It catalogs 100+ plugins, tools, libraries, and resources.
