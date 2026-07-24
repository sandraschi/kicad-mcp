
## [Unreleased] — 2026-07-24 (v4 — Component Browser + Reviews + WebSocket)

### Fixed
- CRITICAL: CORS allow_origin_regex now unconditional with Tailscale/LAN/CGNAT coverage
- CRITICAL: Added /api/v1/health endpoint (was 404 — broke dashboard health polling)
- CRITICAL: NSIS hooks.nsh process names fixed (kicad-backend → kicad-mcp-backend)
- CRITICAL: tauri.conf.json bundles .env.example instead of .env (security — was leaking API keys)
- CRITICAL: build.ps1 bundles .env.example instead of .env
- CRITICAL: run_server.py now supports dual transport (MCP_HOST/PORT env → HTTP, fallback → stdio)
- VERSION: tauri.conf.json synced to 0.3.0 (was 0.1.0), FastAPI title version synced
- capabilities: Added shell:allow-spawn, shell:allow-execute, core:window:allow-set-focus
- .gitignore: Added .env, .bak, reports/, *.mcpb, *.log, timestamp files
- webapp/start.ps1: Fixed undefined $ProjectRoot variable, added -NoBrowser flag
- webapp/api.ts: Exported API_BASE, added VITE_API_BASE env var override
- TypeScript: Fixed 8 compilation errors (missing npm deps, untyped event, useRef init)
- Python: Fixed bare except:pass in ipc_backend.py (Pattern 1 hardening)
- ruff: Added as dev dependency, fixed lint warnings, formatted all source

### Added
- **Supercharged Component Browser**: Parametric filter bar (package, pin count), grid results with detail slide-out panel showing manufacturer, package, pins, stock, price, datasheet links
- **Design Review Dashboard**: New /reviews page + /review/:id with SVG board viewer, annotation overlay, severity-coded markers, AI DRC audit (mock), shareable review IDs
- **Live WebSocket Bridge**: /ws/board endpoint with subscribe/ping channels, live connection indicator (green pulse dot) on Dashboard
- **Backend**: review_router.py (SQLite reviews + annotations), GET /api/v1/component/{query}, WebSocket endpoint, AI audit endpoint
- **Frontend**: ReviewsPage (list + create), ReviewPage (SVG board + annotations + AI audit sidebar), WebSocket indicator on Dashboard
- **AI PCB Design Co-Pilot**: Full Chat page with skill-first system prompt, 4 personalities (PCB Designer, Component Specialist, DFM Reviewer, Custom), localStorage conversation memory (100-msg cap), example prompts grouped by category, .txt export, LLM provider status indicator, and Ollama/LM Studio auto-discovery
- **3D PCB Viewer**: Three.js interactive board preview on the Dashboard with orbit controls, procedural PCB rendering (traces, components, caps), dark theme, and responsive resize
- **Fabrication Pipeline**: New /fab page with Gerber export + zip, order form (fab house, layers, quantity, color, dimensions), JLCPCB pricing estimate, SQLite-backed order history
- **Backend LLM endpoints**: GET /api/v1/llm/discover (probes Ollama :11434 + LM Studio :1234), POST /api/v1/llm/chat (proxy to local LLM with Ollama/OAI-compatible fallback), GET /api/v1/skills (list + fetch SKILL.md content)
- **PCB Design Skill**: Full SKILL.md with tool categories, design workflow guidance, example sequences for placement/routing/export
- **Fab Router**: SQLite-backed fab_orders table, POST /api/v1/fab/export (zip Gerbers), POST /api/v1/fab/order, GET /api/v1/fab/orders
- SPEC.md: Full product specification for all 6 proposed features
- .env.example: Template for KiCad configuration (no real secrets)
- glama.json: Fleet MCP registry metadata
- llms-full.txt: Comprehensive LLM context document
- Session context injection: .claude-plugin/plugin.json + hooks/hooks.json, .cursorrules, .windsurfrules, .github/copilot-instructions.md, .opencode/skills/kicad-mcp/SKILL.md
- reports/ directory with assess-2026-07-24.md report
- just mcpb-pack recipe for MCPB bundle generation
- data-testid attributes on Dashboard KPI cards

### Fixed
- native/src/backend.rs: Added free_port() multi-layer kill (Stop-Process → taskkill → UAC elevated → 240s poll), stdout/stderr stream watching with backend-ready detection, and health check logging
- webapp/index.css: Added color-scheme: dark for native form controls

## [Unreleased] — 2026-06-14

### Fixed
- Tauri build: resolved Rust crate conflict (brotli/alloc-no-stdlib)
- Tauri build: fixed PyInstaller path mismatch (hyphen to underscore in src dirs)
- Tauri build: fixed TypeScript errors (unused imports, useRef arg, import.meta.env)
- Tauri CORS: allow_origins includes tauri://localhost for WebView access

### Added
- CUA-NSIS: just cua-nsis-test recipe, smoke script, config
- CUA-NSIS: build.ps1 now copies NSIS installer to dist/
- CUA-NSIS: 11-phase smoke test (install, launch, WebView OCR, diagnostics, uninstall)
- CUA-NSIS: local certification — all 11 phases pass locally (2026-06-14)

# Changelog

## [0.3.0] — 2026-05-29

### Added — Hybrid KiCad install (stable 10.x + 11 nightly IPC)

- **`docs/NIGHTLY_HEADLESS.md`** — full guide: side-by-side install, env vars, Cursor `mcp.json`, backend selection, troubleshooting, file-format warnings
- **`kicad_install.py`** — discovers Windows KiCad installs; `resolve_stable_cli()` prefers 10.x without `api-server`; `resolve_ipc_cli()` requires `kicad-cli api-server`
- **`ipc_backend.py`** — headless CRUD session via `kipy.KiCad(headless=True)` and nightly `kicad-cli api-server` child process
- **`crud_router.py`** — unified dispatch: IPC → TCP `kc_bridge` → none
- **`scripts/probe_ipc_headless.py`** — probe stable/IPC CLIs, kipy, optional board load
- **Optional dependency** `[project.optional-dependencies] ipc = ["kicad-python>=0.7"]` — install with `uv sync --extra ipc`
- **Tests:** `test_kicad_install.py`, `test_crud_router.py` (14 total passing)
- **Environment variables:** `KICAD_IPC_CLI_PATH`, `KICAD_MCP_CRUD_BACKEND`, `KICAD_MCP_IPC_ENABLED`

### Changed

- **`server.py` lifespan** — picks `crud_backend` (`ipc` | `tcp` | `none`) on startup; shuts down IPC session on exit
- **`kicad_status` / `/api/v1/status`** — reports `kicad_ipc_cli_path`, `kicad_ipc_version`, `ipc_api_server`, `ipc_python_installed`, `crud_backend` (`bridge_mode` is legacy alias)
- **`tools/pcb.py`** — CRUD tools route through `crud_send` instead of raw TCP bridge only
- **Webapp Dashboard** — shows CRUD backend, IPC nightly status, kipy install hint
- **Fleet:** `MASTER_MCP_CONFIG.json` and user `mcp.json` updated with hybrid env + `--extra ipc`
- **Docs:** README, SETUP, ARCHITECTURE, KICAD_API, API, llms.txt, AGENTS.md, INSTALL.md; mcp-central-docs project pages refreshed

### IPC headless coverage (v0.3.0)

| Operation | IPC | Notes |
|-----------|:---:|-------|
| pcb_load / info / list components/nets/tracks | ✅ | |
| pcb_get_component | ✅ | |
| pcb_add_track / pcb_add_via / pcb_save | ✅ | |
| pcb_set_board_outline | ⚠️ | experimental on nightlies |
| pcb_place_component | ❌ | falls back to TCP bridge or error |
| DRC / STEP / Gerber / all exports | — | stable `KICAD_CLI_PATH` lane (unchanged) |

### Known limitations

- Requires **KiCad 11 dev nightly** with `api-server` for headless CRUD; stable 10.0.3 alone stays export-only until nightly is installed
- Boards saved by 11 nightly may use a newer file format than 10.0.3 — use copies for agent experiments
- `pcb_place_component` via IPC not wired yet; use `KICAD_MCP_CRUD_BACKEND=tcp` + `kc_bridge.py` as fallback

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


