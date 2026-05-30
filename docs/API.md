# API Reference

## MCP Transport

All 39 tools available via FastMCP SSE/HTTP:

```
POST /mcp     — JSON-RPC over HTTP
GET  /sse     — Server-Sent Events stream
```

### Client Example

```python
from mcp import ClientSession

async with ClientSession(server_url="http://localhost:11016/mcp") as session:
    result = await session.call_tool("kicad_status", {})
```

## REST API

Base URL: `http://localhost:11016/api/v1`

### Status

```
GET /api/v1/status
→ {
  "server": "kicad-mcp",
  "version": "0.3.0",
  "kicad_available": bool,
  "kicad_version": str,
  "kicad_cli_path": str,
  "kicad_ipc_cli_path": str | null,
  "kicad_ipc_version": str | null,
  "ipc_api_server": bool,
  "ipc_python_installed": bool,
  "crud_backend": "ipc" | "tcp" | "none",
  "bridge_mode": "ipc" | "tcp" | "none",
  "pcb_loaded": str | null,
  "sch_loaded": str | null,
  "uptime_s": int
}
```

### List Tools

```
GET /api/v1/tools
→ {"tools": ["pcb_load", ...], "count": 39}
```

### Call Any Tool

```
POST /api/v1/control/{tool_name}
Body: {"file_name": "board.kicad_pcb", ...}
→ {"success": bool, "data": {...}}
```

### Files

```
POST /api/v1/upload          — upload .kicad_pcb/.kicad_sch file
GET  /api/v1/list?dir=uploads — list uploaded/generated files
GET  /api/v1/download/{name}  — download a file
```

## Tool Signatures

All 39 tools use the standard return schema:

```python
{"success": bool, "message": str, "data": dict | list | None}
```

### PCB Tools

| Tool | Args | Returns |
|------|------|---------|
| `pcb_load` | file_name | path, loaded |
| `pcb_info` | file_name="" | layer_count, component_count, ... |
| `pcb_list_components` | file_name="" | [{reference, value, footprint, ...}] |
| `pcb_list_nets` | file_name="" | [{name, code, pad_count, ...}] |
| `pcb_list_tracks` | file_name="" | [{type, layer, width, start, end}] |
| `pcb_get_component` | reference | {reference, value, pads, ...} |
| `pcb_drc` | file_name, severity | [{type, message, severity}] |
| `pcb_export_step` | file_name, output_name | path, size_kb |
| `pcb_export_gerber` | file_name, output_dir_name | dir, files |
| `pcb_export_pos` | file_name, side, format, output_name | path, size_kb |
| `pcb_export_dxf` | file_name, output_name, layers | path, size_kb |
| `pcb_export_svg` | file_name, output_name, layers | path/files |
| `pcb_export_pdf` | file_name, output_name | path, size_kb |
| `pcb_export_vrml` | file_name, output_name | path, size_kb |
| `pcb_export_glb` | file_name, output_name | path, size_kb |
| `pcb_export_ipc2581` | file_name, output_name, version | path, size_kb |
| `pcb_export_odbpp` | file_name, output_name, compress | path/dir |
| `pcb_place_component` | library, footprint, reference, value, x_mm, y_mm, rotation_deg, layer | reference |
| `pcb_add_track` | start_x/y, end_x/y, layer, width_mm, net_name | length_mm |
| `pcb_add_via` | x_mm, y_mm, diameter_mm, drill_mm, net_name | position, diameter |
| `pcb_save` | file_name="" | path, saved |
| `pcb_set_board_outline` | points[{x,y}] | vertices |

### Schematic Tools

| Tool | Args | Returns |
|------|------|---------|
| `sch_load` | file_name | path |
| `sch_info` | file_name="" | sheets, symbols, nets |
| `sch_erc` | file_name, severity | [{type, message, severity}] |
| `sch_export_netlist` | file_name, output_name | path, size_kb |
| `sch_export_python_bom` | file_name, output_name | path, size_kb |
| `sch_export_pdf` | file_name, output_name | path, size_kb |
| `sch_export_svg` | file_name, output_name | path/files |
| `sch_export_dxf` | file_name, output_name | path, size_kb |

### BOM Tools

| Tool | Args | Returns |
|------|------|---------|
| `bom_generate` | file_name, format, group_by | total_components, bom |

### Library Tools

| Tool | Args | Returns |
|------|------|---------|
| `lib_list_footprints` | library, search, limit | [{name, library}] |
| `lib_list_symbols` | library, search, limit | [{name, library}] |
| `lib_find_footprint` | query, limit | [{name, library}] |
| `lib_find_symbol` | query, limit | [{name, library}] |
| `fp_export_svg` | footprint, library, output_name | path, size_kb |
| `sym_export_svg` | symbol, library, output_name | path, size_kb |

### Marketplace Tools

| Tool | Args | Returns |
|------|------|---------|
| `marketplace_search` | source, query, topic, limit | [{source, name, url, ...}] |
| `marketplace_categories` | source | [{id, label}] |
| `marketplace_download` | source, repo_name, branch | {files, count} |
| `parts_search` | query, source, limit | [{name, source, type}] |
| `parts_missing` | file_name | {missing_footprints, ...} |

### System Tools

| Tool | Args | Returns |
|------|------|---------|
| `kicad_status` | — | See below |
| `kicad_supported_commands` | — | {commands: [{name, description}]} |

#### `kicad_status` response (v0.3.0)

| Field | Type | Description |
|-------|------|-------------|
| `success` | bool | Always true if server running |
| `kicad_available` | bool | Stable export CLI found |
| `kicad_cli_path` | str | Path to stable `kicad-cli` (10.x preferred) |
| `kicad_ipc_cli_path` | str \| null | Nightly CLI with `api-server`, if found |
| `version` | str | Stable KiCad version string |
| `kicad_ipc_version` | str \| null | Nightly version string |
| `ipc_api_server` | bool | Nightly exposes `api-server` subcommand |
| `ipc_python_installed` | bool | `kicad-python` (kipy) importable |
| `crud_backend` | str | Active CRUD lane: `ipc`, `tcp`, or `none` |
| `bridge_mode` | str | Legacy alias of `crud_backend` |
| `work_dir` | str | `%TEMP%\kicad_mcp_work` or override |
| `uploads_dir` / `outputs_dir` | str | Upload and export directories |
| `uptime_s` | int | Server uptime seconds |
