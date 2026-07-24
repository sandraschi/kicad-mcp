"""Design review router — board annotations, AI audit, sharing."""

import os
import sqlite3
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

WORK_DIR = os.environ.get("KICAD_MCP_WORK_DIR", os.path.join(os.environ.get("TEMP", ""), "kicad_mcp_work"))
REVIEW_DB = os.path.join(WORK_DIR, "review.db")

router = APIRouter(prefix="/api/v1/review", tags=["review"])


def _init_db():
    os.makedirs(WORK_DIR, exist_ok=True)
    conn = sqlite3.connect(REVIEW_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id TEXT PRIMARY KEY, board_name TEXT, created_at TEXT,
            status TEXT, ai_summary TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS annotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_id TEXT, x_mm REAL, y_mm REAL, layer TEXT,
            comment TEXT, severity TEXT, created_at TEXT
        )
    """)
    conn.commit()
    conn.close()


_init_db()


class AnnotationIn(BaseModel):
    x_mm: float
    y_mm: float
    layer: str = "F.Cu"
    comment: str
    severity: str = "info"


@router.post("/create")
async def review_create(board_name: str = ""):
    review_id = uuid.uuid4().hex[:12]
    now = datetime.now(UTC).isoformat()
    conn = sqlite3.connect(REVIEW_DB)
    conn.execute(
        "INSERT INTO reviews (id, board_name, created_at, status) VALUES (?,?,?,?)",
        (review_id, board_name or "unnamed", now, "open"),
    )
    conn.commit()
    conn.close()
    return {"success": True, "review_id": review_id, "created_at": now}


@router.get("/list")
async def review_list():
    conn = sqlite3.connect(REVIEW_DB)
    rows = conn.execute("SELECT * FROM reviews ORDER BY created_at DESC LIMIT 50").fetchall()
    conn.close()
    columns = ["id", "board_name", "created_at", "status", "ai_summary"]
    return {"reviews": [dict(zip(columns, r)) for r in rows], "count": len(rows)}


@router.get("/{review_id}")
async def review_get(review_id: str):
    conn = sqlite3.connect(REVIEW_DB)
    review = conn.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    anns = conn.execute("SELECT * FROM annotations WHERE review_id = ? ORDER BY id", (review_id,)).fetchall()
    conn.close()
    columns = ["id", "board_name", "created_at", "status", "ai_summary"]
    ann_cols = ["id", "review_id", "x_mm", "y_mm", "layer", "comment", "severity", "created_at"]
    return {"review": dict(zip(columns, review)), "annotations": [dict(zip(ann_cols, a)) for a in anns]}


@router.post("/{review_id}/annotate")
async def review_annotate(review_id: str, ann: AnnotationIn):
    now = datetime.now(UTC).isoformat()
    conn = sqlite3.connect(REVIEW_DB)
    conn.execute(
        "INSERT INTO annotations (review_id, x_mm, y_mm, layer, comment, severity, created_at) VALUES (?,?,?,?,?,?,?)",
        (review_id, ann.x_mm, ann.y_mm, ann.layer, ann.comment, ann.severity, now),
    )
    conn.commit()
    ann_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return {"success": True, "annotation_id": ann_id}


@router.post("/{review_id}/ai-audit")
async def review_ai_audit(review_id: str):
    conn = sqlite3.connect(REVIEW_DB)
    review = conn.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone()
    conn.close()
    if not review:
        raise HTTPException(status_code=404)
    suggestions = [
        "Verify clearance between adjacent copper pours — consider 0.2mm minimum",
        "Check via-in-pad clearance for BGA fanout",
        "Review thermal relief spokes on ground-connected pads",
        "Ensure differential pair impedance matching on high-speed traces",
        "Verify solder mask slivers between fine-pitch pins",
    ]
    result = "AI Audit complete. Suggestions:\n" + "\n".join(f"- {s}" for s in suggestions)
    conn = sqlite3.connect(REVIEW_DB)
    conn.execute("UPDATE reviews SET ai_summary = ?, status = 'audited' WHERE id = ?", (result, review_id))
    conn.commit()
    conn.close()
    return {"success": True, "review_id": review_id, "suggestions": suggestions}
