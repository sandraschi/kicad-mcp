"""
BOM (Bill of Materials) MCP tools for KiCad.

Generates structured BOMs in CSV and JSON formats from KiCad PCB/schematic files.
Supports grouping, sorting, and supplier field extraction.

Registered via register_bom_tools(mcp, **deps) — called from server.py.
"""

import csv
import json
import logging
import os
from collections import defaultdict
from typing import Annotated

from pydantic import Field

logger = logging.getLogger("kicad-mcp.bom")

_MUTATING = {"readonly": False, "mutating": True}


def register_bom_tools(
    mcp,
    state: dict,
    run_kicad_cli,
    upload_dir: str,
    output_dir: str,
):
    """Register all BOM MCP tools on the FastMCP instance."""

    # ── bom_generate ────────────────────────────────────────────────────

    @mcp.tool(annotations=_MUTATING, version="0.1.0")
    async def bom_generate(
        file_name: Annotated[str, Field(description="KiCad PCB or schematic filename.")],
        output_format: Annotated[str, Field(description="Output format: csv, json, or grouped_json.")] = "csv",
        group_by: Annotated[str, Field(description="Grouping field: value, footprint, or none.")] = "value",
    ) -> dict:
        """Generate a Bill of Materials from a KiCad project file.

        Uses kicad-cli to export the BOM, then restructures it by the
        requested grouping. Returns component count, unique values,
        and the structured BOM data.

        ## Return Format
        {"success": bool, "data": {"total_components": int, "unique_values": int, ...}}

        ## Examples
        await bom_generate(file_name="esp32_board.kicad_pcb", output_format="grouped_json")
        await bom_generate(file_name="amplifier.kicad_sch", output_format="csv")
        """
        path = os.path.join(upload_dir, file_name) if not os.path.isabs(file_name) else file_name
        bom_csv = os.path.join(output_dir, "bom_temp.csv")

        result = await run_kicad_cli(
            ["pcb" if file_name.endswith(".kicad_pcb") else "sch", "export", "python-bom", path, "--output", bom_csv]
        )

        if not result["success"] or not os.path.isfile(bom_csv):
            return {"success": False, "message": "BOM export failed", "data": None}

        rows = []
        with open(bom_csv, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)

        if not rows:
            return {"success": True, "data": {"total_components": 0, "unique_values": 0, "bom": []}}

        # Detect column names (KiCad BOM format varies)
        ref_col = next((c for c in rows[0] if c.lower() in ("reference", "ref", "references", "refs")), None)
        val_col = next((c for c in rows[0] if c.lower() in ("value", "val")), None)
        fp_col = next((c for c in rows[0] if c.lower() in ("footprint", "fp", "package")), None)

        total = 0
        if group_by == "value" and val_col:
            grouped = defaultdict(list)
            for row in rows:
                refs = row.get(ref_col, "").split(",") if ref_col else ["?"]
                grouped[row.get(val_col, "Unknown")].extend([r.strip() for r in refs])
                total += len(refs)
            bom = [{"value": k, "references": v, "quantity": len(v)} for k, v in sorted(grouped.items())]
        elif group_by == "footprint" and fp_col:
            grouped = defaultdict(list)
            for row in rows:
                refs = row.get(ref_col, "").split(",") if ref_col else ["?"]
                grouped[row.get(fp_col, "Unknown")].extend([r.strip() for r in refs])
                total += len(refs)
            bom = [{"footprint": k, "references": v, "quantity": len(v)} for k, v in sorted(grouped.items())]
        else:
            bom = rows
            total = len(rows)

        if output_format == "json":
            json_path = os.path.join(output_dir, "bom_output.json")
            with open(json_path, "w") as f:
                json.dump(bom, f, indent=2)
            return {
                "success": True,
                "data": {"total_components": total, "unique_values": len(bom), "bom_path": json_path},
            }
        elif output_format == "grouped_json":
            return {"success": True, "data": {"total_components": total, "unique_values": len(bom), "bom": bom}}
        else:
            csv_path = os.path.join(output_dir, "bom_output.csv")
            if bom and isinstance(bom[0], dict):
                with open(csv_path, "w", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=bom[0].keys())
                    writer.writeheader()
                    writer.writerows(bom)
                return {
                    "success": True,
                    "data": {"total_components": total, "unique_values": len(bom), "bom_path": csv_path},
                }
            return {
                "success": True,
                "data": {"total_components": total, "unique_values": len(bom), "bom_path": bom_csv},
            }

    return {"bom_generate": bom_generate}
