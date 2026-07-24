"""Probe hybrid KiCad install: stable CLI, IPC nightly, and optional board load."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from kicad_mcp.ipc_backend import IpcHeadlessBackend
from kicad_mcp.kicad_install import (
    discover_cli_installs,
    ipc_python_available,
    resolve_ipc_cli,
    resolve_stable_cli,
)


async def _probe_board(backend: IpcHeadlessBackend, pcb_path: str) -> dict:
    load = await backend.send("pcb_load", {"path": pcb_path})
    if not load.get("success"):
        return {"load": load}
    info = await backend.send("pcb_info", {})
    components = await backend.send("pcb_list_components", {})
    return {"load": load, "info": info, "components": components}


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe KiCad hybrid IPC headless path")
    parser.add_argument("--kicad-cli", dest="kicad_cli", help="Override KICAD_IPC_CLI_PATH")
    parser.add_argument("--pcb", help="Optional .kicad_pcb to load (use a copy)")
    parser.add_argument("--json", action="store_true", help="Emit JSON only")
    args = parser.parse_args()

    stable = resolve_stable_cli()
    ipc = resolve_ipc_cli(args.kicad_cli)
    installs = discover_cli_installs()

    report: dict = {
        "stable_cli": None if stable is None else {"path": stable.path, "version": stable.version},
        "ipc_cli": None
        if ipc is None
        else {"path": ipc.path, "version": ipc.version, "api_server": ipc.has_api_server},
        "ipc_python_installed": ipc_python_available(),
        "discovered": [{"path": i.path, "version": i.version, "api_server": i.has_api_server} for i in installs],
    }

    if ipc and ipc.has_api_server and ipc_python_available():
        backend = IpcHeadlessBackend(ipc.path)
        try:
            ping = asyncio.run(backend.send("ping"))
            report["ipc_ping"] = ping
            if args.pcb:
                report["board_probe"] = asyncio.run(_probe_board(backend, args.pcb))
        finally:
            asyncio.run(backend.close())
    elif ipc and not ipc_python_available():
        report["ipc_ping"] = {"success": False, "error": "kicad-python (kipy) not installed - run: uv sync --extra ipc"}
    elif ipc is None:
        report["ipc_ping"] = {
            "success": False,
            "error": "No IPC CLI with api-server found - install KiCad 11 nightly (docs/NIGHTLY_HEADLESS.md)",
        }

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("KiCad hybrid probe")
        print("==================")
        if stable:
            print(f"Stable CLI: {stable.path} ({stable.version})")
        else:
            print("Stable CLI: not found")
        if ipc:
            print(f"IPC CLI:    {ipc.path} ({ipc.version}) api-server={ipc.has_api_server}")
        else:
            print("IPC CLI:    not found (no api-server)")
        print(f"kipy:       {ipc_python_available()}")
        print(f"IPC ping:   {report.get('ipc_ping')}")
        if args.pcb and "board_probe" in report:
            print(f"Board probe: {json.dumps(report['board_probe'], indent=2)}")

    ok = bool(report.get("ipc_ping", {}).get("success"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
