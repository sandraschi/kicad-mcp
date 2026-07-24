"""Fabrication pipeline router — Gerber export, zip, order tracking."""

import os
import sqlite3
import time
import zipfile
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

WORK_DIR = os.environ.get("KICAD_MCP_WORK_DIR", os.path.join(os.environ.get("TEMP", ""), "kicad_mcp_work"))
FAB_DB = os.path.join(WORK_DIR, "fab_orders.db")
OUTPUT_DIR = os.path.join(WORK_DIR, "output")

router = APIRouter(prefix="/api/v1/fab", tags=["fab"])


def _init_db():
    os.makedirs(WORK_DIR, exist_ok=True)
    conn = sqlite3.connect(FAB_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fab_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            board_name TEXT, created_at TEXT, status TEXT,
            gerber_zip_path TEXT, fab_house TEXT, order_ref TEXT,
            layer_count INTEGER, quantity INTEGER, pcb_color TEXT,
            dimensions TEXT
        )
    """)
    conn.commit()
    conn.close()


_init_db()


class OrderRequest(BaseModel):
    board_name: str
    fab_house: str = "jlcpcb"
    quantity: int = 5
    layer_count: int = 2
    pcb_color: str = "green"
    width_mm: float = 100.0
    height_mm: float = 100.0


@router.post("/export")
async def fab_export(board_name: str = ""):
    """Zip Gerber outputs for fabrication."""
    if not board_name:
        files = sorted(os.listdir(OUTPUT_DIR)) if os.path.isdir(OUTPUT_DIR) else []
        return {"success": False, "error": "board_name required", "files_available": files[:20]}
    gerber_dir = os.path.join(OUTPUT_DIR, board_name.replace(".", "_") + "_gerber")
    zip_name = board_name.replace(".", "_") + "_fab.zip"
    zip_path = os.path.join(OUTPUT_DIR, zip_name)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        added = 0
        if os.path.isdir(gerber_dir):
            for f in sorted(os.listdir(gerber_dir)):
                fp = os.path.join(gerber_dir, f)
                if os.path.isfile(fp):
                    zf.write(fp, f)
                    added += 1
    return {"success": True, "zip_path": zip_name, "file_count": added, "size_bytes": os.path.getsize(zip_path)}


@router.post("/order")
async def fab_order(req: OrderRequest):
    """Create a fabrication order record."""
    conn = sqlite3.connect(FAB_DB)
    now = datetime.now(UTC).isoformat()
    order_ref = f"KICAD-{int(time.time())}"
    conn.execute(
        "INSERT INTO fab_orders (board_name, created_at, status, fab_house, order_ref, layer_count, quantity, pcb_color, dimensions) VALUES (?,?,?,?,?,?,?,?,?)",
        (
            req.board_name,
            now,
            "pending",
            req.fab_house,
            order_ref,
            req.layer_count,
            req.quantity,
            req.pcb_color,
            f"{req.width_mm}x{req.height_mm}mm",
        ),
    )
    conn.commit()
    order_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return {"success": True, "order_id": order_id, "order_ref": order_ref, "status": "pending", "created_at": now}


@router.get("/orders")
async def fab_list_orders():
    """List fabrication order history."""
    conn = sqlite3.connect(FAB_DB)
    rows = conn.execute("SELECT * FROM fab_orders ORDER BY id DESC LIMIT 50").fetchall()
    conn.close()
    columns = [
        "id",
        "board_name",
        "created_at",
        "status",
        "gerber_zip_path",
        "fab_house",
        "order_ref",
        "layer_count",
        "quantity",
        "pcb_color",
        "dimensions",
    ]
    return {"orders": [dict(zip(columns, r)) for r in rows], "count": len(rows)}


@router.get("/orders/{order_id}")
async def fab_get_order(order_id: int):
    conn = sqlite3.connect(FAB_DB)
    row = conn.execute("SELECT * FROM fab_orders WHERE id = ?", (order_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Order not found")
    columns = [
        "id",
        "board_name",
        "created_at",
        "status",
        "gerber_zip_path",
        "fab_house",
        "order_ref",
        "layer_count",
        "quantity",
        "pcb_color",
        "dimensions",
    ]
    return dict(zip(columns, row))
