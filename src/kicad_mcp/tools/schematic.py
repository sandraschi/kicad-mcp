"""
Schematic MCP tools for KiCad eeschema.

Provides schematic loading, inspection, symbol/connection listing,
ERC checking, and netlist export.

Registered via register_schematic_tools(mcp, **deps) — called from server.py.
"""

import json
import logging
import os
from typing import Annotated

from pydantic import Field

logger = logging.getLogger("kicad-mcp.schematic")

_READ_ONLY = {"readonly": True}
_MUTATING = {"readonly": False, "mutating": True}


def register_schematic_tools(
    mcp,
    state: dict,
    bridge_send,
    run_kicad_cli,
    upload_dir: str,
    output_dir: str,
):
    """Register all Schematic MCP tools on the FastMCP instance."""

    # ── sch_load ────────────────────────────────────────────────────────

    @mcp.tool(annotations=_READ_ONLY, version="0.1.0")
    async def sch_load(
        file_name: Annotated[
            str, Field(description="KiCad schematic filename in the uploads directory (e.g. 'project.kicad_sch').")
        ],
    ) -> dict:
        """Load a .kicad_sch schematic file.

        ## Return Format
        {"success": bool, "message": str, "data": {"path": str}}

        ## Examples
        await sch_load(file_name="amplifier.kicad_sch")
        """
        path = os.path.join(upload_dir, file_name)
        if not os.path.isfile(path):
            return {"success": False, "message": f"File not found: {file_name}", "data": None}

        state["sch_loaded"] = path
        return {"success": True, "message": f"Loaded {file_name}", "data": {"path": path}}

    # ── sch_info ────────────────────────────────────────────────────────

    @mcp.tool(annotations=_READ_ONLY, version="0.1.0")
    async def sch_info(
        file_name: Annotated[str, Field(description="KiCad schematic filename (uses last loaded if empty).")] = "",
    ) -> dict:
        """Get schematic metadata: sheet count, symbol count, net count.

        ## Return Format
        {"success": bool, "data": {"sheets": int, "symbols": int, "nets": int, ...}}

        ## Examples
        await sch_info(file_name="amplifier.kicad_sch")
        """
        if not file_name:
            file_name = state.get("sch_loaded", "")
        if not file_name:
            return {"success": False, "message": "No schematic loaded", "data": None}

        path = os.path.join(upload_dir, file_name) if not os.path.isabs(file_name) else file_name
        result = await run_kicad_cli(["sch", "info", path])
        if result["success"]:
            try:
                data = json.loads(result["stdout"])
                return {"success": True, "data": data}
            except json.JSONDecodeError:
                return {"success": True, "data": {"raw": result["stdout"]}}
        return {"success": False, "message": result.get("stderr", "Failed to get schematic info"), "data": None}

    # ── sch_erc ─────────────────────────────────────────────────────────

    @mcp.tool(annotations=_READ_ONLY, version="0.1.0")
    async def sch_erc(
        file_name: Annotated[str, Field(description="KiCad schematic filename.")],
        severity: Annotated[str, Field(description="Minimum severity: error, warning, or all.")] = "warning",
    ) -> dict:
        """Run Electrical Rules Check and return violations.

        ## Return Format
        {"success": bool, "data": {"violations": [...], "count": int}}

        ## Examples
        await sch_erc(file_name="amplifier.kicad_sch")
        await sch_erc(file_name="amplifier.kicad_sch", severity="error")
        """
        path = os.path.join(upload_dir, file_name) if not os.path.isabs(file_name) else file_name
        report_path = os.path.join(output_dir, "erc_report.json")

        result = await run_kicad_cli(["sch", "erc", path, "--severity", severity, "--output", report_path])
        if result["success"]:
            if os.path.isfile(report_path):
                with open(report_path) as f:
                    erc_data = json.load(f)
                violations = erc_data.get("violations", [])
                return {"success": True, "data": {"violations": violations, "count": len(violations)}}
            return {"success": True, "data": {"raw": result["stdout"]}}
        return {"success": False, "message": result.get("stderr", "ERC failed"), "data": None}

    # ── sch_export_netlist ──────────────────────────────────────────────

    @mcp.tool(annotations=_MUTATING, version="0.1.0")
    async def sch_export_netlist(
        file_name: Annotated[str, Field(description="KiCad schematic filename.")],
        output_name: Annotated[str, Field(description="Output netlist filename.")] = "netlist.net",
    ) -> dict:
        """Export the schematic netlist for PCB layout or external tools.

        ## Return Format
        {"success": bool, "output": str, "data": {"path": str, "size_kb": float}}

        ## Examples
        await sch_export_netlist(file_name="amplifier.kicad_sch")
        """
        path = os.path.join(upload_dir, file_name) if not os.path.isabs(file_name) else file_name
        output_path = os.path.join(output_dir, output_name)

        result = await run_kicad_cli(["sch", "export", "netlist", path, "--output", output_path])
        if result["success"] and os.path.isfile(output_path):
            size_kb = os.path.getsize(output_path) / 1024
            return {"success": True, "output": output_name, "data": {"path": output_path, "size_kb": size_kb}}
        return {
            "success": False,
            "message": result.get("stderr", "Netlist export failed"),
            "output": output_name,
            "data": None,
        }

    # ── sch_export_python_bom ───────────────────────────────────────────

    @mcp.tool(annotations=_MUTATING, version="0.1.0")
    async def sch_export_python_bom(
        file_name: Annotated[str, Field(description="KiCad schematic filename.")],
        output_name: Annotated[str, Field(description="Output XML/CSV filename.")] = "bom_output.xml",
    ) -> dict:
        """Export BOM from schematic using KiCad's built-in BOM generator.

        ## Return Format
        {"success": bool, "output": str, "data": {"path": str, "size_kb": float}}

        ## Examples
        await sch_export_python_bom(file_name="amplifier.kicad_sch")
        """
        path = os.path.join(upload_dir, file_name) if not os.path.isabs(file_name) else file_name
        output_path = os.path.join(output_dir, output_name)

        result = await run_kicad_cli(["sch", "export", "python-bom", path, "--output", output_path])
        if result["success"] and os.path.isfile(output_path):
            size_kb = os.path.getsize(output_path) / 1024
            return {"success": True, "output": output_name, "data": {"path": output_path, "size_kb": size_kb}}
        return {
            "success": False,
            "message": result.get("stderr", "BOM export failed"),
            "output": output_name,
            "data": None,
        }

    # ── sch_export_pdf ──────────────────────────────────────────────────

    @mcp.tool(annotations=_MUTATING, version="0.1.0")
    async def sch_export_pdf(
        file_name: Annotated[str, Field(description="KiCad schematic filename.")],
        output_name: Annotated[str, Field(description="Output PDF filename.")] = "schematic.pdf",
    ) -> dict:
        """Export the schematic as a PDF document.

        ## Return Format
        {"success": bool, "output": str, "data": {"path": str, "size_kb": float}}

        ## Examples
        await sch_export_pdf(file_name="amplifier.kicad_sch")
        """
        path = os.path.join(upload_dir, file_name) if not os.path.isabs(file_name) else file_name
        output_path = os.path.join(output_dir, output_name)
        result = await run_kicad_cli(["sch", "export", "pdf", path, "--output", output_path])
        if result["success"] and os.path.isfile(output_path):
            return {
                "success": True,
                "output": output_name,
                "data": {"path": output_path, "size_kb": os.path.getsize(output_path) / 1024},
            }
        return {
            "success": False,
            "message": result.get("stderr", "PDF export failed"),
            "output": output_name,
            "data": None,
        }

    # ── sch_export_svg ──────────────────────────────────────────────────

    @mcp.tool(annotations=_MUTATING, version="0.1.0")
    async def sch_export_svg(
        file_name: Annotated[str, Field(description="KiCad schematic filename.")],
        output_name: Annotated[
            str, Field(description="Output SVG filename (per-sheet if multipage).")
        ] = "schematic.svg",
    ) -> dict:
        """Export the schematic as SVG for documentation.

        ## Return Format
        {"success": bool, "output": str, "data": {"path": str, "size_kb": float}}

        ## Examples
        await sch_export_svg(file_name="amplifier.kicad_sch")
        """
        path = os.path.join(upload_dir, file_name) if not os.path.isabs(file_name) else file_name
        output_path = os.path.join(output_dir, output_name)
        result = await run_kicad_cli(["sch", "export", "svg", path, "--output", output_path])
        if result["success"]:
            if os.path.isfile(output_path):
                return {
                    "success": True,
                    "output": output_name,
                    "data": {"path": output_path, "size_kb": os.path.getsize(output_path) / 1024},
                }
            svg_dir = os.path.dirname(output_path)
            svg_files = [f for f in os.listdir(svg_dir) if f.endswith(".svg")] if os.path.isdir(svg_dir) else []
            return {"success": True, "data": {"files": svg_files, "count": len(svg_files)}}
        return {
            "success": False,
            "message": result.get("stderr", "SVG export failed"),
            "output": output_name,
            "data": None,
        }

    # ── sch_export_dxf ──────────────────────────────────────────────────

    @mcp.tool(annotations=_MUTATING, version="0.1.0")
    async def sch_export_dxf(
        file_name: Annotated[str, Field(description="KiCad schematic filename.")],
        output_name: Annotated[str, Field(description="Output DXF filename.")] = "schematic.dxf",
    ) -> dict:
        """Export the schematic as DXF for mechanical CAD import.

        ## Return Format
        {"success": bool, "output": str, "data": {"path": str, "size_kb": float}}

        ## Examples
        await sch_export_dxf(file_name="amplifier.kicad_sch")
        """
        path = os.path.join(upload_dir, file_name) if not os.path.isabs(file_name) else file_name
        output_path = os.path.join(output_dir, output_name)
        result = await run_kicad_cli(["sch", "export", "dxf", path, "--output", output_path])
        if result["success"] and os.path.isfile(output_path):
            return {
                "success": True,
                "output": output_name,
                "data": {"path": output_path, "size_kb": os.path.getsize(output_path) / 1024},
            }
        return {
            "success": False,
            "message": result.get("stderr", "DXF export failed"),
            "output": output_name,
            "data": None,
        }

    # ── Return tool dict ───────────────────────────────────────────────

    return {
        "sch_load": sch_load,
        "sch_info": sch_info,
        "sch_erc": sch_erc,
        "sch_export_netlist": sch_export_netlist,
        "sch_export_python_bom": sch_export_python_bom,
        "sch_export_pdf": sch_export_pdf,
        "sch_export_svg": sch_export_svg,
        "sch_export_dxf": sch_export_dxf,
    }
