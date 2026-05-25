# Tool Catalog

39 MCP tools across 6 categories. All tools use SOTA docstring protocol:
`Annotated[T, Field(description="...")]` parameter docs, no `Args:` blocks,
`## Return Format` and `## Examples` sections.

## PCB Operations (17 tools)

### Inspection & Loading

| Tool | Annotation | Backend | Description |
|------|-----------|---------|-------------|
| `pcb_load` | READ_ONLY | bridge / state | Load a .kicad_pcb file |
| `pcb_info` | READ_ONLY | bridge / kicad-cli | Board metadata, layers, counts |
| `pcb_list_components` | READ_ONLY | bridge / kicad-cli | All footprints with ref/value/position |
| `pcb_list_nets` | READ_ONLY | bridge only | All nets with pad connections |
| `pcb_list_tracks` | READ_ONLY | bridge only | All tracks/vias with coordinates |
| `pcb_get_component` | READ_ONLY | bridge only | Single component with pads/nets |
| `pcb_drc` | READ_ONLY | bridge / kicad-cli | Design rule check violations |

### Manufacturing Export

| Tool | Annotation | Backend | Format |
|------|-----------|---------|--------|
| `pcb_export_step` | MUTATING | bridge / kicad-cli | STEP 3D model (enclosure design) |
| `pcb_export_gerber` | MUTATING | kicad-cli | Gerber + drill files |
| `pcb_export_pos` | MUTATING | kicad-cli | Pick-and-place CSV |
| `pcb_export_dxf` | MUTATING | kicad-cli | DXF (mechanical CAD) |
| `pcb_export_svg` | MUTATING | kicad-cli | SVG layers |
| `pcb_export_pdf` | MUTATING | kicad-cli | PDF document |
| `pcb_export_vrml` | MUTATING | kicad-cli | VRML 3D model |
| `pcb_export_glb` | MUTATING | kicad-cli | GLB 3D model (web) |
| `pcb_export_ipc2581` | MUTATING | kicad-cli | IPC-2581 fabrication |
| `pcb_export_odbpp` | MUTATING | kicad-cli 9+ | ODB++ fabrication |

### Board Editing (bridge required)

| Tool | Annotation | Description |
|------|-----------|-------------|
| `pcb_place_component` | MUTATING | Place a footprint from library |
| `pcb_add_track` | MUTATING | Route a copper track |
| `pcb_add_via` | MUTATING | Add a through via |
| `pcb_save` | MUTATING | Persist board to file |
| `pcb_set_board_outline` | MUTATING | Define board edge polygon |

## Schematic Operations (8 tools)

### Inspection

| Tool | Annotation | Description |
|------|-----------|-------------|
| `sch_load` | READ_ONLY | Load a .kicad_sch file |
| `sch_info` | READ_ONLY | Sheet/symbol/net metadata |
| `sch_erc` | READ_ONLY | Electrical rules check |

### Export

| Tool | Annotation | Format |
|------|-----------|--------|
| `sch_export_netlist` | MUTATING | Netlist for PCB layout |
| `sch_export_python_bom` | MUTATING | XML BOM |
| `sch_export_pdf` | MUTATING | PDF document |
| `sch_export_svg` | MUTATING | SVG image |
| `sch_export_dxf` | MUTATING | DXF (mechanical CAD) |

## BOM Operations (1 tool)

| Tool | Annotation | Description |
|------|-----------|-------------|
| `bom_generate` | MUTATING | Structured BOM (CSV, JSON, grouped) |

## Library Operations (6 tools)

| Tool | Annotation | Description |
|------|-----------|-------------|
| `lib_list_footprints` | READ_ONLY | List/search footprint libraries |
| `lib_list_symbols` | READ_ONLY | List/search symbol libraries |
| `lib_find_footprint` | READ_ONLY | Search footprints by query |
| `lib_find_symbol` | READ_ONLY | Search symbols by query |
| `fp_export_svg` | MUTATING | Export footprint as SVG |
| `sym_export_svg` | MUTATING | Export symbol as SVG |

## Marketplace Operations (5 tools)

| Tool | Annotation | Source | Description |
|------|-----------|--------|-------------|
| `marketplace_search` | READ_ONLY | GitHub/Kitspace/SnapEDA | Search KiCad projects |
| `marketplace_categories` | READ_ONLY | Static | List available topics |
| `marketplace_download` | MUTATING | GitHub/Kitspace/SnapEDA | Download to uploads/ |
| `parts_search` | READ_ONLY | SnapEDA + built-in | Search components |
| `parts_missing` | READ_ONLY | PCB s-expr | Find missing footprints |

## System Operations (2 tools)

| Tool | Annotation | Description |
|------|-----------|-------------|
| `kicad_status` | READ_ONLY | KiCad version, bridge mode, uptime |
| `kicad_supported_commands` | READ_ONLY | List kicad-cli commands |

## Annotations Legend

| Annotation | Meaning |
|-----------|---------|
| `READ_ONLY` | Does not modify any state or files |
| `MUTATING` | Creates/modifies files or board objects |
| `DESTRUCTIVE` | Deletes files or board objects (none currently) |
