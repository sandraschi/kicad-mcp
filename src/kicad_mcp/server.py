"""
FastMCP 3.2 Unified Gateway for KiCad PCB/schematic operations.

Architecture:
  MCP client/tool → kicad-cli subprocess (headless CLI)
                   → kc_bridge TCP (GUI-dependent operations, internal to KiCad)
                   → JSON response

The server uses three execution modes:
  1. kicad-cli subprocess — headless export, DRC, ERC (always available if KiCad installed)
  2. TCP bridge — pcbnew operations requiring the KiCad GUI (board manipulation)
  3. Direct pcbnew import — if KiCad Python libs are on sys.path (limited support)
"""

import asyncio
import json
import logging
import os
import subprocess
import time
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastmcp import FastMCP

from kicad_mcp.tools import (
    register_bom_tools,
    register_library_tools,
    register_marketplace_tools,
    register_pcb_tools,
    register_schematic_tools,
)

logger = logging.getLogger("kicad-mcp")

_READ_ONLY = {"readonly": True}
_START_TIME = time.time()

# ── Config ───────────────────────────────────────────────────────────────────

KICAD_CLI_PATH = os.environ.get("KICAD_CLI_PATH") or next(
    (
        p
        for p in [
            r"C:\Program Files\KiCad\8.0\bin\kicad-cli.exe",
            r"C:\Program Files\KiCad\7.0\bin\kicad-cli.exe",
            r"C:\Program Files\KiCad\9.0\bin\kicad-cli.exe",
        ]
        if os.path.isfile(p)
    ),
    "kicad-cli",  # fallback to PATH
)

BRIDGE_PORT = int(os.environ.get("KC_BRIDGE_PORT", "11018"))
BRIDGE_SCRIPT = Path(__file__).parent / "kc_bridge.py"

WORK_DIR = os.environ.get("KICAD_MCP_WORK_DIR", os.path.join(os.environ.get("TEMP", ""), "kicad_mcp_work"))
os.makedirs(WORK_DIR, exist_ok=True)

UPLOAD_DIR = os.path.join(WORK_DIR, "uploads")
OUTPUT_DIR = os.path.join(WORK_DIR, "output")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── State ────────────────────────────────────────────────────────────────────

_state: dict = {}
_req_id = 0
_bridge_reader: asyncio.StreamReader | None = None
_bridge_writer: asyncio.StreamWriter | None = None


# ── Bridge Communication ─────────────────────────────────────────────────────


async def _bridge_send(method: str, params: dict | None = None, timeout: float = 120) -> dict:
    """Send a JSON command to the KiCad bridge and return the response."""
    global _req_id
    _req_id += 1
    req = {"id": _req_id, "method": method, "params": params or {}}
    payload = json.dumps(req) + "\n"

    if _bridge_writer is None:
        return {"success": False, "error": "KiCad bridge not connected", "fallback": True}

    try:
        _bridge_writer.write(payload.encode("utf-8"))
        await _bridge_writer.drain()
        data = await asyncio.wait_for(_bridge_reader.readline(), timeout=timeout)
        return json.loads(data.decode("utf-8"))
    except TimeoutError:
        return {"success": False, "error": f"Bridge timeout ({timeout}s)", "fallback": True}
    except Exception as e:
        return {"success": False, "error": str(e), "fallback": True}


async def _bridge_connect():
    """Connect to the KiCad bridge TCP socket."""
    global _bridge_reader, _bridge_writer
    try:
        r, w = await asyncio.wait_for(asyncio.open_connection("127.0.0.1", BRIDGE_PORT), timeout=10)
        _bridge_reader, _bridge_writer = r, w
        resp = await _bridge_send("ping", timeout=5)
        return resp.get("data") == "pong"
    except Exception as e:
        logger.warning("Bridge connect failed: %s", e)
        _bridge_reader = _bridge_writer = None
        return False


# ── kicad-cli Subprocess ─────────────────────────────────────────────────────


async def _run_kicad_cli(args: list[str], timeout: int = 60) -> dict:
    """Run kicad-cli with given arguments and return {success, stdout, stderr, returncode}."""
    try:
        proc = await asyncio.create_subprocess_exec(
            KICAD_CLI_PATH,
            *args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        stdout = out.decode("utf-8", errors="replace") if out else ""
        stderr = err.decode("utf-8", errors="replace") if err else ""
        return {"success": proc.returncode == 0, "stdout": stdout, "stderr": stderr, "returncode": proc.returncode}
    except FileNotFoundError:
        return {"success": False, "stdout": "", "stderr": f"kicad-cli not found at {KICAD_CLI_PATH}", "returncode": -1}
    except TimeoutError:
        return {"success": False, "stdout": "", "stderr": f"kicad-cli timed out ({timeout}s)", "returncode": -1}
    except Exception as e:
        return {"success": False, "stdout": "", "stderr": str(e), "returncode": -1}


def _find_kicad_cli() -> str | None:
    """Check if kicad-cli is available and return its path."""
    if os.path.isfile(KICAD_CLI_PATH):
        return KICAD_CLI_PATH
    try:
        r = subprocess.run(["where", "kicad-cli"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip().splitlines()[0]
    except Exception:
        pass
    return None


# ── Lifespan ─────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: detect KiCad, attempt bridge connection, serve."""
    logger.info("KiCad MCP startup")

    _state["kicad_ok"] = False
    _state["kicad_cli_path"] = None
    _state["kicad_version"] = None
    _state["bridge_mode"] = "none"
    _state["pcb_loaded"] = None
    _state["sch_loaded"] = None

    # 1. Find kicad-cli
    cli_path = _find_kicad_cli()
    if cli_path:
        _state["kicad_cli_path"] = cli_path
        _state["kicad_ok"] = True

        # Get version
        try:
            r = subprocess.run([cli_path, "--version"], capture_output=True, text=True, timeout=10)
            _state["kicad_version"] = r.stdout.strip() or r.stderr.strip()
        except Exception:
            _state["kicad_version"] = "unknown"

    # 2. Check if KiCad bridge is already running
    bridge_already = False
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection("127.0.0.1", BRIDGE_PORT), timeout=1)
        writer.close()
        await writer.wait_closed()
        bridge_already = True
        logger.info("KiCad bridge already running on port %s", BRIDGE_PORT)
    except (TimeoutError, ConnectionRefusedError, OSError):
        pass

    if bridge_already:
        for attempt in range(5):
            await asyncio.sleep(1)
            if await _bridge_connect():
                _state["bridge_mode"] = "tcp"
                logger.info("Connected to existing KiCad bridge")
                break
        if not _state.get("bridge_mode") == "tcp":
            logger.warning("Existing bridge found but could not connect")
    else:
        _state["bridge_mode"] = "cli" if _state["kicad_ok"] else "none"
        logger.info("Bridge not running; using kicad-cli mode: %s", _state["bridge_mode"])

    _state["work_dir"] = WORK_DIR
    yield

    # Shutdown
    if _bridge_writer and not bridge_already:
        try:
            _bridge_writer.close()
            await _bridge_writer.wait_closed()
        except Exception:
            pass


# ── FastAPI App ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="KiCad MCP",
    description="KiCad PCB/schematic design automation — MCP tools + REST API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── FastMCP Instance ─────────────────────────────────────────────────────────

mcp = FastMCP.from_fastapi(app, name="KiCad MCP")

# ── Register Tool Modules ────────────────────────────────────────────────────

_pcb_tools = register_pcb_tools(
    mcp=mcp,
    state=_state,
    bridge_send=_bridge_send,
    run_kicad_cli=_run_kicad_cli,
    work_dir=WORK_DIR,
    output_dir=OUTPUT_DIR,
    upload_dir=UPLOAD_DIR,
)

_sch_tools = register_schematic_tools(
    mcp=mcp,
    state=_state,
    bridge_send=_bridge_send,
    run_kicad_cli=_run_kicad_cli,
    upload_dir=UPLOAD_DIR,
    output_dir=OUTPUT_DIR,
)

_bom_tools = register_bom_tools(
    mcp=mcp,
    state=_state,
    run_kicad_cli=_run_kicad_cli,
    upload_dir=UPLOAD_DIR,
    output_dir=OUTPUT_DIR,
)

_lib_tools = register_library_tools(
    mcp=mcp,
    state=_state,
    run_kicad_cli=_run_kicad_cli,
    output_dir=OUTPUT_DIR,
)

_mk_tools = register_marketplace_tools(
    mcp=mcp,
    state=_state,
    run_kicad_cli=_run_kicad_cli,
    upload_dir=UPLOAD_DIR,
    output_dir=OUTPUT_DIR,
)

# Combine all REST tool dicts for dispatch
_all_tools = {}
_all_tools.update(_pcb_tools)
_all_tools.update(_sch_tools)
_all_tools.update(_bom_tools)
_all_tools.update(_lib_tools)
_all_tools.update(_mk_tools)
# Server-level tools are registered below but not in register closures;
# we add them to _all_tools after definition so REST dispatch works.


# ── Server-Level MCP Tools ───────────────────────────────────────────────────


@mcp.tool(annotations=_READ_ONLY, version="0.1.0")
async def kicad_status() -> dict:
    """Check KiCad availability, version, and bridge status.

    ## Return Format
    {"success": bool, "kicad_available": bool, "version": str, "bridge_mode": str, "work_dir": str}

    ## Examples
    await kicad_status()
    """
    return {
        "success": True,
        "kicad_available": _state.get("kicad_ok", False),
        "kicad_cli_path": _state.get("kicad_cli_path"),
        "version": _state.get("kicad_version"),
        "bridge_mode": _state.get("bridge_mode", "none"),
        "work_dir": WORK_DIR,
        "uploads_dir": UPLOAD_DIR,
        "outputs_dir": OUTPUT_DIR,
        "uptime_s": int(time.time() - _START_TIME),
    }


@mcp.tool(annotations=_READ_ONLY, version="0.1.0")
async def kicad_supported_commands() -> dict:
    """List kicad-cli supported subcommands and their descriptions.

    ## Return Format
    {"success": bool, "data": {"commands": [{"name": str, "description": str}, ...]}}

    ## Examples
    await kicad_supported_commands()
    """
    result = await _run_kicad_cli(["--help"])
    if result["success"]:
        return {"success": True, "data": {"raw": result["stdout"]}}
    return {"success": False, "message": "kicad-cli unavailable", "data": None}


# Add server-level tools to REST dispatch
_all_tools["kicad_status"] = kicad_status
_all_tools["kicad_supported_commands"] = kicad_supported_commands


# ── REST Endpoints ───────────────────────────────────────────────────────────


@app.get("/api/v1/status")
async def api_status():
    return {
        "server": "kicad-mcp",
        "version": "0.1.0",
        "kicad_available": _state.get("kicad_ok", False),
        "kicad_version": _state.get("kicad_version"),
        "bridge_mode": _state.get("bridge_mode"),
        "pcb_loaded": _state.get("pcb_loaded"),
        "sch_loaded": _state.get("sch_loaded"),
        "uptime_s": int(time.time() - _START_TIME),
    }


@app.get("/api/v1/tools")
async def api_list_tools():
    return {"tools": sorted(_all_tools.keys()), "count": len(_all_tools)}


@app.post("/api/v1/control/{tool_name}")
async def api_control_tool(tool_name: str, request: Request):
    """Dispatch REST calls to registered MCP tools by name."""
    tool_fn = _all_tools.get(tool_name)
    if tool_fn is None:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")
    try:
        body = await request.json()
    except Exception:
        body = {}
    result = await tool_fn(**body)
    return result


@app.post("/api/v1/upload")
async def api_upload(file: UploadFile):
    """Upload a KiCad project file (PCB, schematic, etc.)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename")
    safe_name = Path(file.filename).name
    dest = os.path.join(UPLOAD_DIR, safe_name)
    content = await file.read()
    with open(dest, "wb") as f:
        f.write(content)
    return {"success": True, "filename": safe_name, "size_bytes": len(content)}


@app.get("/api/v1/list")
async def api_list_files(dir: str = "uploads"):
    """List files in uploads or outputs directory."""
    target = UPLOAD_DIR if dir == "uploads" else OUTPUT_DIR
    files = []
    if os.path.isdir(target):
        for f in sorted(os.listdir(target)):
            fp = os.path.join(target, f)
            if os.path.isfile(fp):
                files.append({"name": f, "size_bytes": os.path.getsize(fp)})
    return {"directory": dir, "files": files, "count": len(files)}


@app.get("/api/v1/download/{file_name}")
async def api_download(file_name: str, dir: str = "outputs"):
    """Download a generated file from outputs or uploads."""
    target = OUTPUT_DIR if dir == "outputs" else UPLOAD_DIR
    path = os.path.join(target, file_name)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail=f"File not found: {file_name}")
    return FileResponse(path, filename=file_name)


# ── Main Entry Point ─────────────────────────────────────────────────────────


def main():
    import argparse

    parser = argparse.ArgumentParser(description="KiCad MCP Server")
    parser.add_argument("--mode", default="dual", choices=["dual", "sse", "stdio", "http"], help="Server mode")
    parser.add_argument("--port", type=int, default=11016, help="Port for HTTP/SSE modes")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    args = parser.parse_args()

    if args.mode == "stdio":
        # FastMCP handles stdio transport natively
        mcp.run(transport="stdio")
    else:
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
