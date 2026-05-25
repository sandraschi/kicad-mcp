# Changelog

## [0.2.0] — 2026-05-25

### Added
- 8 PCB export wrappers: pcb_export_pos (pick-and-place), pcb_export_dxf, pcb_export_svg, pcb_export_pdf, pcb_export_vrml, pcb_export_glb, pcb_export_ipc2581, pcb_export_odbpp (KiCad 9.0+)
- 3 Schematic export wrappers: sch_export_pdf, sch_export_svg, sch_export_dxf
- 2 Library export wrappers: fp_export_svg, sym_export_svg
- PCB CRUD tools: pcb_place_component, pcb_add_track, pcb_add_via, pcb_save, pcb_set_board_outline
- Bridge handlers: pcb_place_component, pcb_add_track, pcb_add_via, pcb_save (4 new pcbnew API methods)
- All bridge handlers use `_MUTATING` annotation and require TCP bridge

### Fixed
- kc_bridge.py: `pcb_set_board_outline` bug — was creating N polygons with all N vertices each instead of 1 polygon with N vertices
- kc_bridge.py: docstring now correctly lists only implemented methods (removed 7 ghosts)
- kc_bridge.py: default port 11014 → 11018 (fleet standard)

## [0.1.1] — 2026-05-25

### Changed
- Re-ported from 11012/11013/11014 to 11016/11017/11018 (port conflict with tahoma2d-mcp and google-ai-mcp)
- All 26 tools now have SOTA annotations (`READ_ONLY` / `MUTATING`) and `version="0.1.0"`

### Added
- Marketplace tools: marketplace_search, marketplace_categories, marketplace_download, parts_search, parts_missing (5 tools, bringing total to 26)
- Playwright e2e tests (12 tests: 8 frontend, 4 REST API)
- CI/CD GitHub Actions workflow (lint, typecheck, pytest, e2e)
- Ports 11016/11017/11018 registered in fleet WEBAPP_PORTS.md

### Fixed
- start.ps1 rewritten to SOTA 2026 standard (param block, readiness polling, auto-browser-open, ScriptRoot)
- justfile `web` recipe: direct npx instead of cmd /c wrapper
- server.py: DRY `_READ_ONLY` constant for server-level tools
- README: tool count corrected (19 → 26), marketplace row added

## [0.1.0] — 2026-05-23

### Added
- Initial release with 21 MCP tools across 5 categories (now 26)
- Unified FastAPI + FastMCP gateway server
- KiCad TCP bridge (kc_bridge.py) for pcbnew operations
- PCB tools: load, inspect, list components/nets/tracks, DRC, STEP/Gerber export
- Schematic tools: load, inspect, ERC, netlist/BOM export
- BOM generator with grouping by value/footprint
- Library browser: footprint and symbol search
- Vite + React webapp with 8 pages
- justfile with bootstrap, serve, dev, lint, test, health, e2e recipes
- kicad-cli subprocess fallback for headless operations
