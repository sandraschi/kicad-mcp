# KiCad 11 Nightly — Headless IPC Path (Hybrid Install)

> **Fleet mirror:** `mcp-central-docs/projects/kicad-mcp/HYBRID_INSTALL.md`  
> **Cursor config:** `mcp-central-docs/projects/kicad-mcp/CURSOR_MCP.md`  
> **Version:** kicad-mcp 0.3.0 (2026-05-29)

This guide describes how to run **kicad-mcp** with a **hybrid KiCad install**:
| Role | KiCad version | Binary | Used for |
|------|---------------|--------|----------|
| **Stable export lane** | 10.0.x (production) | `kicad-cli` from 10.0 | Gerber, STEP, DRC/ERC, BOM, library CLI, schematic exports |
| **Headless CRUD lane** | 11.x **dev nightly** | `kicad-cli api-server` | PCB read/write via IPC (`kicad-python` / `kipy`) — no GUI, no SWIG bridge |

Stable KiCad remains your fab-trusted path. Nightly KiCad is an **experimental CRUD backend** until 11.0 ships (~Jan 2027).

---

## Why hybrid?

- **KiCad 10** has mature `kicad-cli` but IPC only talks to a **running GUI**.
- **KiCad 11** adds `kicad-cli api-server` — headless IPC ([master CLI docs](https://docs.kicad.org/master/en/cli/cli.html)).
- **SWIG pcbnew is removed in 11 nightlies** — the old TCP bridge (`kc_bridge.py`) will not work on nightly-only installs.

kicad-mcp routes work like this:

```
Exports / DRC / ERC / library CLI  →  KICAD_CLI_PATH (stable 10.x)
PCB CRUD (place, route, save, …)   →  IPC headless (11 nightly)  →  else TCP bridge  →  else read-only
```

---

## Prerequisites

- Windows 10/11 (this doc is PowerShell-first; Linux/macOS paths differ)
- **KiCad 10.0.x** stable — already installed at `C:\Program Files\KiCad\10.0\`
- **KiCad 11 dev nightly** — separate install (see below)
- Python 3.12+ with `uv`
- kicad-mcp with IPC extras: `uv sync --extra ipc`

---

## Step 1 — Install KiCad 11 nightly (side-by-side)

1. Open [KiCad downloads — Windows nightlies](https://downloads.kicad.org/kicad/windows/explore/nightlies).
2. Download the latest **full** Windows x64 nightly installer.
3. Install to a **separate directory**, e.g.:
   - `C:\Program Files\KiCad\11.0\` (when nightly reports 11.x), or
   - `C:\Program Files\KiCad\10.99\` / custom path if the build still identifies as 10.99.

Nightlies use a **separate settings tree** under `%APPDATA%\kicad\<major.minor>\` — they do not overwrite 10.0 settings.

**Do not** uninstall KiCad 10.0.3 — kicad-mcp keeps it for exports.

### Verify nightly has `api-server`

```powershell
& "C:\Program Files\KiCad\11.0\bin\kicad-cli.exe" version
& "C:\Program Files\KiCad\11.0\bin\kicad-cli.exe" api-server --help
```

Expected: help text mentioning *Run the KiCad IPC API server in headless mode*.

If `api-server` is missing, the build is too old — download a newer nightly.

---

## Step 2 — Install kicad-python (IPC bindings)

From the kicad-mcp repo:

```powershell
Set-Location D:\Dev\repos\kicad-mcp
uv sync --extra ipc
```

Optional: pin to GitLab main if PyPI lags the nightly protobuf schema:

```powershell
uv pip install "kicad-python @ git+https://gitlab.com/kicad/code/kicad-python.git"
```

Quick REPL test (from [kicad-python headless example](https://gitlab.com/kicad/code/kicad-python/-/blob/main/examples/headless.py)):

```powershell
$pcb = "D:\path\to\copy-of-board.kicad_pcb"   # use a COPY — see warnings below
uv run python -m kicad_mcp.scripts.probe_ipc_headless --kicad-cli "C:\Program Files\KiCad\11.0\bin\kicad-cli.exe" --pcb $pcb
```

---

## Step 3 — Configure kicad-mcp environment

Set these for Cursor, federation bootstrap, or local `just serve`:

| Variable | Example | Purpose |
|----------|---------|---------|
| `KICAD_CLI_PATH` | `C:/Program Files/KiCad/10.0/bin/kicad-cli.exe` | **Stable** CLI for exports/DRC/ERC |
| `KICAD_IPC_CLI_PATH` | `C:/Program Files/KiCad/11.0/bin/kicad-cli.exe` | **Nightly** CLI with `api-server` |
| `KICAD_MCP_CRUD_BACKEND` | `auto` | `auto` \| `ipc` \| `tcp` \| `none` |
| `KICAD_MCP_IPC_ENABLED` | `auto` | `auto` \| `1` \| `0` — force IPC on/off |

### Cursor `mcp.json` snippet

```json
"kicad-mcp": {
  "command": "C:/Users/sandr/.local/bin/uv.exe",
  "args": [
    "--directory", "D:/Dev/repos/kicad-mcp",
    "run", "--extra", "ipc",
    "python", "-m", "kicad_mcp.server", "--mode", "stdio"
  ],
  "cwd": "D:/Dev/repos/kicad-mcp",
  "env": {
    "PYTHONUNBUFFERED": "1",
    "FASTMCP_BANNER": "0",
    "FASTMCP_UPDATE_CHECK": "0",
    "KICAD_CLI_PATH": "C:/Program Files/KiCad/10.0/bin/kicad-cli.exe",
    "KICAD_IPC_CLI_PATH": "C:/Program Files/KiCad/11.0/bin/kicad-cli.exe",
    "KICAD_MCP_CRUD_BACKEND": "auto"
  }
}
```

After editing, restart Cursor MCP.

---

## Step 4 — Probe and status

```powershell
Set-Location D:\Dev\repos\kicad-mcp
uv run python -m kicad_mcp.scripts.probe_ipc_headless
```

Or call MCP tool `kicad_status` — response includes:

| Field | Meaning |
|-------|---------|
| `kicad_cli_path` | Stable export CLI |
| `kicad_ipc_cli_path` | Nightly IPC CLI (if found) |
| `ipc_api_server` | `true` if nightly exposes `api-server` |
| `crud_backend` | `ipc`, `tcp`, or `none` |
| `bridge_mode` | Legacy alias; same as `crud_backend` for MCP clients |

---

## Backend selection (`auto` mode)

On startup kicad-mcp:

1. Resolves stable CLI → sets export lane (10.x preferred over 11.x).
2. Resolves IPC CLI → checks `api-server --help`.
3. Tries `import kipy` (kicad-python).
4. Picks CRUD backend:
   - **IPC** if IPC CLI + api-server + kipy available
   - else **TCP** if `kc_bridge.py` already listening on `KC_BRIDGE_PORT` (11018)
   - else **none** (exports still work; CRUD tools error with guidance)

Force IPC only:

```powershell
$env:KICAD_MCP_CRUD_BACKEND = "ipc"
```

Force legacy GUI bridge:

```powershell
$env:KICAD_MCP_CRUD_BACKEND = "tcp"
```

---

## What works on nightlies today (expect gaps)

| Operation | IPC headless | Stable CLI fallback |
|-----------|:------------:|:-------------------:|
| Load / info / list components/nets/tracks | ✅ | partial (info only) |
| Add track / via | ✅ (11 nightly) | ❌ |
| Save board | ✅ | ❌ |
| Place footprint from library | ⚠️ experimental | ❌ |
| Board outline | ⚠️ experimental | ❌ |
| DRC | ⚠️ prefer stable CLI | ✅ |
| Gerber / STEP / GLB / ODB++ | ❌ use stable CLI | ✅ |
| Schematic CRUD | ❌ not in IPC yet | export-only CLI |

IPC **export/plot** APIs exist in 11 docs but are newer than CRUD — kicad-mcp still uses **stable kicad-cli** for all manufacturing exports.

---

## File format warning

Boards saved by **KiCad 11 nightly** may use a newer file format than **10.0.3**.

- Keep **golden projects on 10.x** until 11.0 stable.
- Use **copies** in `%TEMP%\kicad_mcp_work\uploads\` for agent experiments.
- Never let an agent overwrite your only production `.kicad_pcb` without a backup.

---

## Troubleshooting

### `api-server` not found

You are on stable 10.x only. Install dev nightly or set `KICAD_IPC_CLI_PATH` to the nightly binary.

### `No module named 'kipy'`

```powershell
uv sync --extra ipc
```

### `check_version()` fails / protobuf errors

Nightly KiCad and `kicad-python` protobufs are out of sync. Update both:

```powershell
# Newer nightly installer
uv pip install --upgrade kicad-python
# or install from GitLab main (see Step 2)
```

### IPC connects but CRUD fails mid-session

Restart MCP (kills headless `api-server` child). Check `%APPDATA%\kicad\<version>\logs\api.log` with `EnableAPILogging=1` in `kicad_advanced` (see [KiCad IPC debugging](https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-addon-developers/index.html)).

### Still need GUI bridge

If IPC is blocked, open KiCad 10 GUI and run `kc_bridge.py` (see [SETUP.md](./SETUP.md)). Set `KICAD_MCP_CRUD_BACKEND=tcp`.

---

## Roadmap (kicad-mcp)

- [x] Hybrid CLI discovery (`kicad_install.py`)
- [x] IPC headless session + CRUD router (`ipc_backend.py`)
- [x] `kicad_status` reports both CLIs and backend
- [ ] Full `pcb_place_component` via IPC library API
- [ ] IPC export lane (optional) when stable on 11.0
- [ ] Retire TCP bridge default once 11.0 stable + headless is proven

---

## References

- [KiCad IPC API (dev docs)](https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/index.html)
- [Add-on developer guide (headless note)](https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-addon-developers/index.html)
- [Master kicad-cli (api-server)](https://docs.kicad.org/master/en/cli/cli.html)
- [kicad-python / kipy docs](https://docs.kicad.org/kicad-python-main/)
- [SWIG removal timeline (~Feb/Mar 2027)](https://forum.kicad.info/t/migration-schedule-from-the-old-swig-api-to-the-ipc-api/69437)
- In-repo: [KICAD_API.md](./KICAD_API.md), [ARCHITECTURE.md](./ARCHITECTURE.md)
- Fleet: [HYBRID_INSTALL.md](https://github.com/sandraschi/mcp-central-docs/blob/main/projects/kicad-mcp/HYBRID_INSTALL.md), [CURSOR_MCP.md](https://github.com/sandraschi/mcp-central-docs/blob/main/projects/kicad-mcp/CURSOR_MCP.md)

---

## Implementation modules (for contributors)

| Module | Path | Notes |
|--------|------|-------|
| CLI discovery | `src/kicad_mcp/kicad_install.py` | `resolve_stable_cli()`, `resolve_ipc_cli()`, env parsing |
| IPC session | `src/kicad_mcp/ipc_backend.py` | `IpcHeadlessBackend.send(method, params)` |
| Router | `src/kicad_mcp/crud_router.py` | `crud_send(state, bridge, ipc, method)` |
| Lifespan | `src/kicad_mcp/server.py` | Sets `crud_backend`, owns IPC shutdown |
| PCB tools | `src/kicad_mcp/tools/pcb.py` | CRUD via `crud_send`; exports via `run_kicad_cli` |
| Probe CLI | `src/kicad_mcp/scripts/probe_ipc_headless.py` | Operator diagnostics |
