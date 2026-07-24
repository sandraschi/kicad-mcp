"""
FastMCP 3.2 Unified Gateway for KiCad PCB/schematic operations.

Architecture:
  MCP client/tool → kicad-cli subprocess (stable export lane)
                   → IPC headless (KiCad 11 nightly api-server + kicad-python)
                   → kc_bridge TCP (legacy GUI bridge)
                   → JSON response

Execution lanes:
  1. Stable kicad-cli — exports, DRC, ERC, library CLI (KICAD_CLI_PATH, typically 10.x)
  2. IPC headless CRUD — pcb load/save, tracks, vias (KICAD_IPC_CLI_PATH, 11 nightly)
  3. TCP bridge — pcbnew via KiCad GUI + kc_bridge.py (deprecated on 11 nightlies)
"""

import asyncio
import json
import logging
import os
import subprocess
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastmcp import FastMCP
from pydantic import BaseModel

from kicad_mcp.crud_router import crud_send as _crud_send_impl
from kicad_mcp.fab_router import router as fab_router
from kicad_mcp.ipc_backend import IpcHeadlessBackend
from kicad_mcp.kicad_install import (
    ipc_enabled,
    ipc_python_available,
    parse_crud_backend_pref,
    resolve_ipc_cli,
    resolve_stable_cli,
)
from kicad_mcp.review_router import router as review_router
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

_stable_install = resolve_stable_cli()
KICAD_CLI_PATH = _stable_install.path if _stable_install else "kicad-cli"

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
_ipc_backend: IpcHeadlessBackend | None = None


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


async def _ipc_send(method: str, params: dict | None = None) -> dict:
    """Send a bridge-compatible method to the headless IPC backend."""
    if _ipc_backend is None:
        return {"success": False, "error": "IPC backend not initialized", "fallback": True}
    return await _ipc_backend.send(method, params)


async def _crud_send(method: str, params: dict | None = None) -> dict:
    """Route CRUD to IPC headless or TCP bridge based on startup selection."""
    ipc_fn = _ipc_send if _ipc_backend is not None else None
    return await _crud_send_impl(_state, _bridge_send, ipc_fn, method, params)


def _pick_crud_backend(pref: str, ipc_ok: bool, tcp_ok: bool) -> str:
    if pref == "none":
        return "none"
    if pref == "ipc":
        return "ipc" if ipc_ok else "none"
    if pref == "tcp":
        return "tcp" if tcp_ok else "none"
    if ipc_ok:
        return "ipc"
    if tcp_ok:
        return "tcp"
    return "none"


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
    """Startup: detect KiCad installs, pick CRUD backend, serve."""
    global _ipc_backend, KICAD_CLI_PATH
    logger.info("KiCad MCP startup")

    _state["kicad_ok"] = False
    _state["kicad_cli_path"] = None
    _state["kicad_version"] = None
    _state["kicad_ipc_cli_path"] = None
    _state["kicad_ipc_version"] = None
    _state["ipc_api_server"] = False
    _state["ipc_python_installed"] = ipc_python_available()
    _state["crud_backend"] = "none"
    _state["bridge_mode"] = "none"
    _state["pcb_loaded"] = None
    _state["sch_loaded"] = None

    # 1. Stable export lane (10.x preferred)
    stable = resolve_stable_cli()
    if stable and os.path.isfile(stable.path):
        KICAD_CLI_PATH = stable.path
        _state["kicad_cli_path"] = stable.path
        _state["kicad_ok"] = True
        _state["kicad_version"] = stable.version or "unknown"
    else:
        cli_path = _find_kicad_cli()
        if cli_path:
            KICAD_CLI_PATH = cli_path
            _state["kicad_cli_path"] = cli_path
            _state["kicad_ok"] = True
            try:
                r = subprocess.run([cli_path, "--version"], capture_output=True, text=True, timeout=10)
                _state["kicad_version"] = r.stdout.strip() or r.stderr.strip()
            except Exception:
                _state["kicad_version"] = "unknown"

    # 2. IPC nightly lane
    ipc_install = resolve_ipc_cli()
    ipc_ready = False
    if ipc_install and ipc_enabled():
        _state["kicad_ipc_cli_path"] = ipc_install.path
        _state["kicad_ipc_version"] = ipc_install.version
        _state["ipc_api_server"] = ipc_install.has_api_server
        ipc_ready = ipc_install.has_api_server and _state["ipc_python_installed"]
        if ipc_install.has_api_server and not _state["ipc_python_installed"]:
            logger.warning("KiCad IPC CLI found but kicad-python (kipy) not installed — run: uv sync --extra ipc")

    # 3. Legacy TCP bridge (optional)
    bridge_already = False
    tcp_ready = False
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection("127.0.0.1", BRIDGE_PORT), timeout=1)
        writer.close()
        await writer.wait_closed()
        bridge_already = True
        logger.info("KiCad bridge already running on port %s", BRIDGE_PORT)
    except (TimeoutError, ConnectionRefusedError, OSError):
        pass

    if bridge_already:
        for _attempt in range(5):
            await asyncio.sleep(1)
            if await _bridge_connect():
                tcp_ready = True
                logger.info("Connected to existing KiCad bridge")
                break
        if not tcp_ready:
            logger.warning("Existing bridge found but could not connect")

    crud_pref = parse_crud_backend_pref()
    crud_backend = _pick_crud_backend(crud_pref, ipc_ready, tcp_ready)
    _state["crud_backend"] = crud_backend
    _state["bridge_mode"] = crud_backend

    if crud_backend == "ipc" and ipc_install:
        _ipc_backend = IpcHeadlessBackend(ipc_install.path)
        ping = await _ipc_send("ping")
        if ping.get("success"):
            logger.info("IPC headless backend ready (%s)", ipc_install.path)
        else:
            logger.warning("IPC ping failed: %s", ping.get("error"))
    elif crud_backend == "none":
        if _state["kicad_ok"]:
            logger.info("Export lane only (stable kicad-cli); no CRUD backend — see docs/NIGHTLY_HEADLESS.md")
        else:
            logger.warning("KiCad not detected")

    _state["work_dir"] = WORK_DIR
    yield

    if _ipc_backend is not None:
        await _ipc_backend.close()
        _ipc_backend = None

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
    version="0.3.0",
    lifespan=lifespan,
)

app.include_router(fab_router)
app.include_router(review_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:11016",
        "http://127.0.0.1:11017",
        "http://localhost:11016",
        "http://localhost:11017",
        "http://tauri.localhost",
        "https://tauri.localhost",
        "tauri://localhost",
    ],
    allow_origin_regex=r"https?://(?:[a-zA-Z0-9-]+\.ts\.net|.*?\.tail-[a-f0-9]+\.ts\.net|tauri\.localhost|localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|100\.\d{1,3}\.\d{1,3}\.\d{1,3})(?::\d+)?$|^tauri://localhost$",
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
    crud_send=_crud_send,
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
    crud = _state.get("crud_backend", "none")
    return {
        "success": True,
        "kicad_available": _state.get("kicad_ok", False),
        "kicad_cli_path": _state.get("kicad_cli_path"),
        "kicad_ipc_cli_path": _state.get("kicad_ipc_cli_path"),
        "version": _state.get("kicad_version"),
        "kicad_ipc_version": _state.get("kicad_ipc_version"),
        "ipc_api_server": _state.get("ipc_api_server", False),
        "ipc_python_installed": _state.get("ipc_python_installed", False),
        "crud_backend": crud,
        "bridge_mode": crud,
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
    crud = _state.get("crud_backend", "none")
    return {
        "server": "kicad-mcp",
        "version": "0.3.0",
        "kicad_available": _state.get("kicad_ok", False),
        "kicad_version": _state.get("kicad_version"),
        "kicad_cli_path": _state.get("kicad_cli_path"),
        "kicad_ipc_cli_path": _state.get("kicad_ipc_cli_path"),
        "kicad_ipc_version": _state.get("kicad_ipc_version"),
        "ipc_api_server": _state.get("ipc_api_server", False),
        "ipc_python_installed": _state.get("ipc_python_installed", False),
        "crud_backend": crud,
        "bridge_mode": crud,
        "pcb_loaded": _state.get("pcb_loaded"),
        "sch_loaded": _state.get("sch_loaded"),
        "uptime_s": int(time.time() - _START_TIME),
    }


@app.get("/api/v1/health")
async def api_health():
    return {
        "status": "ok",
        "server": "kicad-mcp",
        "version": "0.3.0",
        "uptime_seconds": int(time.time() - _START_TIME),
        "tool_count": len(_all_tools),
        "providers": {
            "kicad_stable": _state.get("kicad_ok", False),
            "crud_backend": _state.get("crud_backend", "none"),
        },
    }


@app.get("/api/v1/diagnostics")
async def api_diagnostics():
    try:
        import psutil

        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent
    except ImportError:
        cpu = mem = disk = None
    return {
        "success": True,
        "backend": {"port": 11016, "status": "running", "uptime": int(time.time() - _START_TIME)},
        "system": {"cpu_percent": cpu, "memory_percent": mem, "disk_percent": disk},
        "tools": {"total": len(_all_tools), "names": sorted(_all_tools.keys())},
        "cua_status": {"tesseract_available": False, "window_found": False},
    }


@app.get("/api/v1/tools")
async def api_list_tools():
    return {"tools": sorted(_all_tools.keys()), "count": len(_all_tools)}


@app.get("/api/v1/skills")
async def api_list_skills():
    skills_dir = Path(__file__).parent / "skills"
    if not skills_dir.is_dir():
        return {"skills": [], "count": 0}
    skills = []
    for d in skills_dir.iterdir():
        skill_md = d / "SKILL.md"
        if skill_md.is_file():
            skills.append({"name": d.name, "title": d.name.replace("-", " ").title()})
    return {"skills": skills, "count": len(skills)}


@app.get("/api/v1/skills/{skill_name}")
async def api_get_skill(skill_name: str):
    skill_path = Path(__file__).parent / "skills" / skill_name / "SKILL.md"
    if skill_path.is_file():
        return {"name": skill_name, "content": skill_path.read_text(encoding="utf-8")}
    return {"name": skill_name, "content": "", "error": "not found"}


@app.get("/api/v1/llm/discover")
async def api_llm_discover():
    """Probe Ollama and LM Studio, return detected providers + models."""
    providers = []
    async with httpx.AsyncClient(timeout=3) as client:
        # Ollama
        try:
            r = await client.get("http://127.0.0.1:11434/api/tags")
            if r.status_code == 200:
                models = [m["name"] for m in r.json().get("models", [])]
                providers.append(
                    {
                        "name": "ollama",
                        "port": 11434,
                        "base": "http://127.0.0.1:11434",
                        "models": models,
                        "status": "detected",
                    }
                )
        except Exception:
            providers.append({"name": "ollama", "port": 11434, "status": "not_found"})
        # LM Studio
        try:
            r = await client.get("http://127.0.0.1:1234/v1/models")
            if r.status_code == 200:
                models = [m["id"] for m in r.json().get("data", [])]
                providers.append(
                    {
                        "name": "lm_studio",
                        "port": 1234,
                        "base": "http://127.0.0.1:1234",
                        "models": models,
                        "status": "detected",
                    }
                )
        except Exception:
            providers.append({"name": "lm_studio", "port": 1234, "status": "not_found"})
    return {"providers": providers, "count": len(providers)}


LLM_CHAT_MODEL = os.environ.get("KICAD_MCP_LLM_MODEL", "llama3.2:latest")
LLM_CHAT_BASE = os.environ.get("KICAD_MCP_LLM_BASE", "http://127.0.0.1:11434")


class ChatRequest(BaseModel):
    model: str = LLM_CHAT_MODEL
    system: str = ""
    messages: list[dict] = []
    stream: bool = False


@app.post("/api/v1/llm/chat")
async def api_llm_chat(req: ChatRequest):
    """Proxy chat completion to local LLM (Ollama or OpenAI-compatible)."""
    base_url = LLM_CHAT_BASE
    model = req.model
    messages = [*([{"role": "system", "content": req.system}] if req.system else []), *req.messages]

    # Try Ollama first
    async with httpx.AsyncClient(timeout=60) as client:
        try:
            r = await client.post(f"{base_url}/api/chat", json={"model": model, "messages": messages, "stream": False})
            if r.status_code == 200:
                data = r.json()
                return {
                    "choices": [
                        {"message": {"role": "assistant", "content": data.get("message", {}).get("content", "")}}
                    ]
                }
        except Exception:
            pass
        # Fallback: OpenAI-compatible endpoint
        try:
            r = await client.post(
                f"{base_url}/v1/chat/completions", json={"model": model, "messages": messages, "stream": False}
            )
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
    return {
        "choices": [{"message": {"role": "assistant", "content": "No local LLM detected. Start Ollama or LM Studio."}}]
    }


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


@app.get("/api/v1/component/{query}")
async def api_component_detail(query: str):
    """Return mock component details for a part number or query."""
    return {
        "success": True,
        "query": query,
        "data": {
            "manufacturer": "Texas Instruments",
            "package": "SOIC-8",
            "pins": 8,
            "description": f"Component matching '{query}' — parametric data",
            "datasheet": f"https://www.ti.com/product/{query}",
            "stock": 12500,
            "price_1k": 0.42,
        },
    }


active_boards: dict[str, set] = {}


@app.websocket("/ws/board")
async def ws_board(websocket: WebSocket):
    await websocket.accept()
    board_id = f"board-{uuid.uuid4().hex[:8]}"
    active_boards[board_id] = set()
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong", "board_id": board_id})
            elif msg.get("type") == "subscribe":
                channel = msg.get("channel", "board")
                active_boards[board_id].add(channel)
                await websocket.send_json({"type": "subscribed", "channel": channel})
    except WebSocketDisconnect:
        pass
    finally:
        active_boards.pop(board_id, None)


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
