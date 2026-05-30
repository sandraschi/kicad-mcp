# kicad-mcp Agent Context

Fleet MCP server for KiCad PCB/schematic automation. **v0.3.0** adds hybrid install support.

## Hybrid KiCad (read first)

| Lane | Env | KiCad |
|------|-----|-------|
| Export / DRC / ERC | `KICAD_CLI_PATH` | 10.0.x stable |
| Headless CRUD | `KICAD_IPC_CLI_PATH` + `--extra ipc` | 11 nightly + kicad-python |

Docs: `docs/NIGHTLY_HEADLESS.md` · Fleet: `mcp-central-docs/projects/kicad-mcp/HYBRID_INSTALL.md`

Probe: `uv run python -m kicad_mcp.scripts.probe_ipc_headless`

Status tool: `kicad_status` → check `crud_backend` (`ipc` | `tcp` | `none`).

## Key modules (v0.3.0)

| Path | Role |
|------|------|
| `src/kicad_mcp/kicad_install.py` | CLI discovery, stable vs IPC resolution |
| `src/kicad_mcp/ipc_backend.py` | Headless kipy session |
| `src/kicad_mcp/crud_router.py` | IPC vs TCP dispatch |
| `src/kicad_mcp/tools/pcb.py` | PCB MCP tools |
| `src/kicad_mcp/kc_bridge.py` | Legacy TCP bridge (KiCad GUI) |

## Quick Ref

```powershell
uv sync --extra ipc
uv run pytest tests/ -q
uv run python -m kicad_mcp.scripts.probe_ipc_headless
just serve
```

## Agent rules

- Use **copies** of `.kicad_pcb` in `%TEMP%\kicad_mcp_work\uploads\` for CRUD experiments.
- Do not save production boards with 11 nightly without backup (format may exceed 10.0.3).
- DRC and manufacturing exports: always stable `KICAD_CLI_PATH`, not IPC.
- If `crud_backend` is `none`, CRUD tools fail — run probe or install nightly.

See `justfile` for bootstrap, serve, lint, test, e2e.
