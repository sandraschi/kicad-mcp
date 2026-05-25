"""
PCB (Printed Circuit Board) MCP tools for KiCad pcbnew.

Provides board loading, inspection, component/net/track listing,
DRC checking, and manufacturing export (STEP, Gerber).

Registered via register_pcb_tools(mcp, **deps) — called from server.py.
"""

import json
import logging
import os
from typing import Annotated

from pydantic import Field

logger = logging.getLogger("kicad-mcp.pcb")

_READ_ONLY = {"readonly": True}
_MUTATING = {"readonly": False, "mutating": True}


def register_pcb_tools(
    mcp,
    state: dict,
    bridge_send,
    run_kicad_cli,
    work_dir: str,
    output_dir: str,
    upload_dir: str,
):
    """Register all PCB MCP tools on the FastMCP instance."""

    # ── pcb_load ────────────────────────────────────────────────────────

    @mcp.tool(annotations=_READ_ONLY, version="0.1.0")
    async def pcb_load(
        file_name: Annotated[
            str, Field(description="KiCad PCB filename in the uploads directory (e.g. 'my_board.kicad_pcb').")
        ],
    ) -> dict:
        """Load a .kicad_pcb file for inspection and manipulation.

        ## Return Format
        {"success": bool, "message": str, "data": {"path": str, "loaded": bool}}

        ## Examples
        await pcb_load(file_name="esp32_board.kicad_pcb")
        """
        path = os.path.join(upload_dir, file_name)
        if not os.path.isfile(path):
            return {"success": False, "message": f"File not found: {file_name}", "data": None}

        if state.get("bridge_mode") == "tcp":
            resp = await bridge_send("pcb_load", {"path": path})
            if resp.get("success"):
                state["pcb_loaded"] = path
                return {"success": True, "message": f"Loaded {file_name}", "data": resp.get("data")}

        state["pcb_loaded"] = path
        return {
            "success": True,
            "message": f"Loaded {file_name} (bridge unavailable; kicad-cli mode)",
            "data": {"path": path},
        }

    # ── pcb_info ────────────────────────────────────────────────────────

    @mcp.tool(annotations=_READ_ONLY, version="0.1.0")
    async def pcb_info(
        file_name: Annotated[str, Field(description="KiCad PCB filename (uses last loaded if empty).")] = "",
    ) -> dict:
        """Get comprehensive board metadata: layers, dimensions, component/net/track counts.

        ## Return Format
        {"success": bool, "data": {"layer_count": int, "component_count": int, "net_count": int, ...}}

        ## Examples
        await pcb_info(file_name="esp32_board.kicad_pcb")
        await pcb_info()  # uses last loaded board
        """
        if not file_name:
            file_name = state.get("pcb_loaded", "")
            if not file_name:
                return {"success": False, "message": "No board loaded", "data": None}
        path = os.path.join(upload_dir, file_name) if not os.path.isabs(file_name) else file_name

        if state.get("bridge_mode") == "tcp":
            resp = await bridge_send("pcb_info", {})
            if resp.get("success"):
                return resp

        # Fallback: use kicad-cli
        result = await run_kicad_cli(["pcb", "info", path])
        if result["success"]:
            try:
                data = json.loads(result["stdout"])
                return {"success": True, "data": data}
            except json.JSONDecodeError:
                return {"success": True, "data": {"raw": result["stdout"]}}
        return {"success": False, "message": result.get("stderr", "Failed to get board info"), "data": None}

    # ── pcb_list_components ─────────────────────────────────────────────

    @mcp.tool(annotations=_READ_ONLY, version="0.1.0")
    async def pcb_list_components(
        file_name: Annotated[str, Field(description="KiCad PCB filename (uses last loaded if empty).")] = "",
    ) -> dict:
        """List all components with reference, value, footprint, layer, and position.

        ## Return Format
        {"success": bool, "data": {"components": [{"reference": str, "value": str, ...}], "count": int}}

        ## Examples
        await pcb_list_components()
        """
        if state.get("bridge_mode") == "tcp":
            resp = await bridge_send("pcb_list_components", {})
            if resp.get("success"):
                return resp

        if not file_name:
            file_name = state.get("pcb_loaded", "")
        if not file_name:
            return {"success": False, "message": "No board loaded and bridge unavailable", "data": None}

        path = os.path.join(upload_dir, file_name) if not os.path.isabs(file_name) else file_name
        result = await run_kicad_cli(
            ["pcb", "export", "bom", path, "--output", os.path.join(output_dir, "bom_temp.csv")]
        )
        if result["success"]:
            import csv

            bom_path = os.path.join(output_dir, "bom_temp.csv")
            components = []
            if os.path.isfile(bom_path):
                with open(bom_path, newline="") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        components.append(
                            {
                                "reference": row.get("Reference", row.get("Ref", "")),
                                "value": row.get("Value", ""),
                                "footprint": row.get("Footprint", ""),
                            }
                        )
                return {"success": True, "data": {"components": components, "count": len(components)}}
        return {"success": False, "message": "Bridge unavailable and kicad-cli BOM export failed", "data": None}

    # ── pcb_list_nets ─────────────────────────────────────────────────

    @mcp.tool(annotations=_READ_ONLY, version="0.1.0")
    async def pcb_list_nets(
        file_name: Annotated[str, Field(description="KiCad PCB filename (uses last loaded if empty).")] = "",
    ) -> dict:
        """List all nets with pad connections.

        ## Return Format
        {"success": bool, "data": {"nets": [{"name": str, "code": int, "pad_count": int, "pads": [...]}], "count": int}}

        ## Examples
        await pcb_list_nets()
        """
        if state.get("bridge_mode") == "tcp":
            resp = await bridge_send("pcb_list_nets", {})
            if resp.get("success"):
                return resp
        return {"success": False, "message": "Requires TCP bridge (KiCad GUI with kc_bridge.py running)", "data": None}

    # ── pcb_list_tracks ───────────────────────────────────────────────

    @mcp.tool(annotations=_READ_ONLY, version="0.1.0")
    async def pcb_list_tracks(
        file_name: Annotated[str, Field(description="KiCad PCB filename (uses last loaded if empty).")] = "",
    ) -> dict:
        """List all tracks and vias with layer, width, and coordinates.

        ## Return Format
        {"success": bool, "data": {"tracks": [...], "count": int}}

        ## Examples
        await pcb_list_tracks()
        """
        if state.get("bridge_mode") == "tcp":
            resp = await bridge_send("pcb_list_tracks", {})
            if resp.get("success"):
                return resp
        return {"success": False, "message": "Requires TCP bridge", "data": None}

    # ── pcb_get_component ─────────────────────────────────────────────

    @mcp.tool(annotations=_READ_ONLY, version="0.1.0")
    async def pcb_get_component(
        reference: Annotated[str, Field(description="Component reference designator (e.g. 'R1', 'U3').")],
    ) -> dict:
        """Get detailed info for a single component including pad positions and nets.

        ## Return Format
        {"success": bool, "data": {"reference": str, "value": str, "pads": [...], ...}}

        ## Examples
        await pcb_get_component(reference="U1")
        """
        if state.get("bridge_mode") == "tcp":
            resp = await bridge_send("pcb_get_component", {"reference": reference})
            return resp
        return {"success": False, "message": "Requires TCP bridge", "data": None}

    # ── pcb_drc ────────────────────────────────────────────────────────

    @mcp.tool(annotations=_READ_ONLY, version="0.1.0")
    async def pcb_drc(
        file_name: Annotated[str, Field(description="KiCad PCB filename.")],
        severity: Annotated[str, Field(description="Minimum severity to report: error, warning, or all.")] = "warning",
    ) -> dict:
        """Run Design Rule Check and return violations.

        ## Return Format
        {"success": bool, "data": {"violations": [...], "count": int}}

        ## Examples
        await pcb_drc(file_name="my_board.kicad_pcb")
        await pcb_drc(file_name="my_board.kicad_pcb", severity="error")
        """
        path = os.path.join(upload_dir, file_name) if not os.path.isabs(file_name) else file_name

        if state.get("bridge_mode") == "tcp":
            resp = await bridge_send("pcb_drc", {})
            if resp.get("success"):
                return resp
            if not resp.get("fallback"):
                return resp

        # kicad-cli fallback
        result = await run_kicad_cli(
            ["pcb", "drc", path, "--severity", severity, "--output", os.path.join(output_dir, "drc_report.json")]
        )
        if result["success"]:
            drc_path = os.path.join(output_dir, "drc_report.json")
            if os.path.isfile(drc_path):
                with open(drc_path) as f:
                    drc_data = json.load(f)
                violations = drc_data.get("violations", [])
                return {"success": True, "data": {"violations": violations, "count": len(violations)}}
            return {"success": True, "data": {"raw": result["stdout"]}}
        return {"success": False, "message": result.get("stderr", "DRC failed"), "data": None}

    # ── pcb_export_step ─────────────────────────────────────────────────

    @mcp.tool(annotations=_MUTATING, version="0.1.0")
    async def pcb_export_step(
        file_name: Annotated[str, Field(description="KiCad PCB filename.")],
        output_name: Annotated[str, Field(description="Output STEP filename (e.g. 'board.step').")] = "board.step",
    ) -> dict:
        """Export the PCB as a STEP 3D model for enclosure design in freecad-mcp.

        ## Return Format
        {"success": bool, "output": str, "data": {"path": str, "size_kb": float}}

        ## Examples
        await pcb_export_step(file_name="esp32.kicad_pcb", output_name="esp32_3d.step")
        """
        path = os.path.join(upload_dir, file_name) if not os.path.isabs(file_name) else file_name
        output_path = os.path.join(output_dir, output_name)

        if state.get("bridge_mode") == "tcp":
            resp = await bridge_send("pcb_export_step", {"path": output_path})
            if resp.get("success"):
                size_kb = os.path.getsize(output_path) / 1024 if os.path.isfile(output_path) else 0
                return {"success": True, "output": output_name, "data": {"path": output_path, "size_kb": size_kb}}
            if not resp.get("fallback"):
                return resp

        # kicad-cli fallback
        result = await run_kicad_cli(["pcb", "export", "step", path, "--output", output_path, "--subst-models"])
        if result["success"] and os.path.isfile(output_path):
            size_kb = os.path.getsize(output_path) / 1024
            return {"success": True, "output": output_name, "data": {"path": output_path, "size_kb": size_kb}}
        return {
            "success": False,
            "message": result.get("stderr", "STEP export failed"),
            "output": output_name,
            "data": None,
        }

    # ── pcb_export_gerber ──────────────────────────────────────────────

    @mcp.tool(annotations=_MUTATING, version="0.1.0")
    async def pcb_export_gerber(
        file_name: Annotated[str, Field(description="KiCad PCB filename.")],
        output_dir_name: Annotated[str, Field(description="Subdirectory name in outputs for Gerber files.")] = "gerber",
    ) -> dict:
        """Export Gerber manufacturing files (layers, drill, BOM, POS).

        ## Return Format
        {"success": bool, "output": str, "data": {"dir": str, "files": [str, ...]}}

        ## Examples
        await pcb_export_gerber(file_name="esp32.kicad_pcb")
        """
        path = os.path.join(upload_dir, file_name) if not os.path.isabs(file_name) else file_name
        gerber_dir = os.path.join(output_dir, output_dir_name)
        os.makedirs(gerber_dir, exist_ok=True)

        result = await run_kicad_cli(["pcb", "export", "gerbers", path, "--output", gerber_dir])
        if not result["success"]:
            return {
                "success": False,
                "message": result.get("stderr", "Gerber export failed"),
                "output": output_dir_name,
                "data": None,
            }

        # Also export drill files
        await run_kicad_cli(["pcb", "export", "drill", path, "--output", gerber_dir])

        files = sorted(os.listdir(gerber_dir)) if os.path.isdir(gerber_dir) else []
        return {"success": True, "output": output_dir_name, "data": {"dir": gerber_dir, "files": files}}

    # ── pcb_export_pos ─────────────────────────────────────────────────

    @mcp.tool(annotations=_MUTATING, version="0.1.0")
    async def pcb_export_pos(
        file_name: Annotated[str, Field(description="KiCad PCB filename.")],
        side: Annotated[str, Field(description="Component side: top, bottom, or both.")] = "both",
        output_format: Annotated[str, Field(description="Output format: csv, ascii, or gerber.")] = "csv",
        output_name: Annotated[str, Field(description="Output filename.")] = "positions.csv",
    ) -> dict:
        """Export pick-and-place (component position) file for assembly.

        ## Return Format
        {"success": bool, "output": str, "data": {"path": str, "size_kb": float}}

        ## Examples
        await pcb_export_pos(file_name="esp32.kicad_pcb", side="top", output_format="csv")
        """
        path = os.path.join(upload_dir, file_name) if not os.path.isabs(file_name) else file_name
        output_path = os.path.join(output_dir, output_name)
        result = await run_kicad_cli(
            ["pcb", "export", "pos", path, "--side", side, "--format", output_format, "--output", output_path]
        )
        if result["success"] and os.path.isfile(output_path):
            return {
                "success": True,
                "output": output_name,
                "data": {"path": output_path, "size_kb": os.path.getsize(output_path) / 1024},
            }
        return {
            "success": False,
            "message": result.get("stderr", "POS export failed"),
            "output": output_name,
            "data": None,
        }

    # ── pcb_export_dxf ────────────────────────────────────────────────

    @mcp.tool(annotations=_MUTATING, version="0.1.0")
    async def pcb_export_dxf(
        file_name: Annotated[str, Field(description="KiCad PCB filename.")],
        output_name: Annotated[str, Field(description="Output DXF filename.")] = "board.dxf",
        layers: Annotated[
            str,
            Field(
                description="Comma-separated layer list. Use 'all' for all layers, 'common' for Copper/Edge.Cuts/Silkscreen."
            ),
        ] = "common",
    ) -> dict:
        """Export the PCB as DXF for mechanical CAD import.

        ## Return Format
        {"success": bool, "output": str, "data": {"path": str, "size_kb": float}}

        ## Examples
        await pcb_export_dxf(file_name="esp32.kicad_pcb")
        await pcb_export_dxf(file_name="esp32.kicad_pcb", layers="F.Cu,B.Cu,Edge.Cuts")
        """
        path = os.path.join(upload_dir, file_name) if not os.path.isabs(file_name) else file_name
        output_path = os.path.join(output_dir, output_name)
        args = ["pcb", "export", "dxf", path, "--output", output_path]
        if layers == "common":
            args.append("--common-layers")
        elif layers != "all":
            args.extend(["--layers", layers])
        result = await run_kicad_cli(args)
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

    # ── pcb_export_svg ────────────────────────────────────────────────

    @mcp.tool(annotations=_MUTATING, version="0.1.0")
    async def pcb_export_svg(
        file_name: Annotated[str, Field(description="KiCad PCB filename.")],
        output_name: Annotated[str, Field(description="Output SVG filename (per-layer if multiple).")] = "board.svg",
        layers: Annotated[str, Field(description="Comma-separated layers or 'all'.")] = "all",
    ) -> dict:
        """Export PCB layers as SVG for documentation.

        ## Return Format
        {"success": bool, "output": str, "data": {"path": str, "size_kb": float}}

        ## Examples
        await pcb_export_svg(file_name="esp32.kicad_pcb", layers="F.Cu,F.Silkscreen")
        """
        path = os.path.join(upload_dir, file_name) if not os.path.isabs(file_name) else file_name
        output_path = os.path.join(output_dir, output_name)
        args = ["pcb", "export", "svg", path, "--output", output_path]
        if layers and layers != "all":
            args.extend(["--layers", layers])
        result = await run_kicad_cli(args)
        if result["success"]:
            if os.path.isfile(output_path):
                return {
                    "success": True,
                    "output": output_name,
                    "data": {"path": output_path, "size_kb": os.path.getsize(output_path) / 1024},
                }
            return {
                "success": True,
                "data": {
                    "raw_stdout": result.get("stdout", ""),
                    "files": [f for f in os.listdir(os.path.dirname(output_path)) if f.endswith(".svg")]
                    if os.path.isdir(os.path.dirname(output_path))
                    else [],
                },
            }
        return {
            "success": False,
            "message": result.get("stderr", "SVG export failed"),
            "output": output_name,
            "data": None,
        }

    # ── pcb_export_pdf ────────────────────────────────────────────────

    @mcp.tool(annotations=_MUTATING, version="0.1.0")
    async def pcb_export_pdf(
        file_name: Annotated[str, Field(description="KiCad PCB filename.")],
        output_name: Annotated[str, Field(description="Output PDF filename.")] = "board.pdf",
    ) -> dict:
        """Export the PCB as a PDF document.

        ## Return Format
        {"success": bool, "output": str, "data": {"path": str, "size_kb": float}}

        ## Examples
        await pcb_export_pdf(file_name="esp32.kicad_pcb")
        """
        path = os.path.join(upload_dir, file_name) if not os.path.isabs(file_name) else file_name
        output_path = os.path.join(output_dir, output_name)
        result = await run_kicad_cli(["pcb", "export", "pdf", path, "--output", output_path])
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

    # ── pcb_export_vrml ───────────────────────────────────────────────

    @mcp.tool(annotations=_MUTATING, version="0.1.0")
    async def pcb_export_vrml(
        file_name: Annotated[str, Field(description="KiCad PCB filename.")],
        output_name: Annotated[str, Field(description="Output VRML filename.")] = "board.wrl",
    ) -> dict:
        """Export the PCB as VRML 3D model.

        ## Return Format
        {"success": bool, "output": str, "data": {"path": str, "size_kb": float}}

        ## Examples
        await pcb_export_vrml(file_name="esp32.kicad_pcb")
        """
        path = os.path.join(upload_dir, file_name) if not os.path.isabs(file_name) else file_name
        output_path = os.path.join(output_dir, output_name)
        result = await run_kicad_cli(["pcb", "export", "vrml", path, "--output", output_path])
        if result["success"] and os.path.isfile(output_path):
            return {
                "success": True,
                "output": output_name,
                "data": {"path": output_path, "size_kb": os.path.getsize(output_path) / 1024},
            }
        return {
            "success": False,
            "message": result.get("stderr", "VRML export failed"),
            "output": output_name,
            "data": None,
        }

    # ── pcb_export_glb ────────────────────────────────────────────────

    @mcp.tool(annotations=_MUTATING, version="0.1.0")
    async def pcb_export_glb(
        file_name: Annotated[str, Field(description="KiCad PCB filename.")],
        output_name: Annotated[str, Field(description="Output GLB filename.")] = "board.glb",
    ) -> dict:
        """Export the PCB as GLB (binary glTF) 3D model for web visualization.

        ## Return Format
        {"success": bool, "output": str, "data": {"path": str, "size_kb": float}}

        ## Examples
        await pcb_export_glb(file_name="esp32.kicad_pcb")
        """
        path = os.path.join(upload_dir, file_name) if not os.path.isabs(file_name) else file_name
        output_path = os.path.join(output_dir, output_name)
        result = await run_kicad_cli(["pcb", "export", "glb", path, "--output", output_path])
        if result["success"] and os.path.isfile(output_path):
            return {
                "success": True,
                "output": output_name,
                "data": {"path": output_path, "size_kb": os.path.getsize(output_path) / 1024},
            }
        return {
            "success": False,
            "message": result.get("stderr", "GLB export failed"),
            "output": output_name,
            "data": None,
        }

    # ── pcb_export_ipc2581 ────────────────────────────────────────────

    @mcp.tool(annotations=_MUTATING, version="0.1.0")
    async def pcb_export_ipc2581(
        file_name: Annotated[str, Field(description="KiCad PCB filename.")],
        output_name: Annotated[str, Field(description="Output IPC-2581 XML filename.")] = "board.ipc2581",
        version: Annotated[str, Field(description="IPC-2581 revision: b or c.")] = "c",
    ) -> dict:
        """Export the PCB in IPC-2581 format for fabrication.

        ## Return Format
        {"success": bool, "output": str, "data": {"path": str, "size_kb": float}}

        ## Examples
        await pcb_export_ipc2581(file_name="esp32.kicad_pcb")
        """
        path = os.path.join(upload_dir, file_name) if not os.path.isabs(file_name) else file_name
        output_path = os.path.join(output_dir, output_name)
        result = await run_kicad_cli(["pcb", "export", "ipc2581", path, "--output", output_path, "--version", version])
        if result["success"] and os.path.isfile(output_path):
            return {
                "success": True,
                "output": output_name,
                "data": {"path": output_path, "size_kb": os.path.getsize(output_path) / 1024},
            }
        return {
            "success": False,
            "message": result.get("stderr", "IPC-2581 export failed"),
            "output": output_name,
            "data": None,
        }

    # ── pcb_export_odbpp ──────────────────────────────────────────────

    @mcp.tool(annotations=_MUTATING, version="0.1.0")
    async def pcb_export_odbpp(
        file_name: Annotated[str, Field(description="KiCad PCB filename.")],
        output_name: Annotated[str, Field(description="Output ODB++ directory or zip name.")] = "board_odb",
        compress: Annotated[str, Field(description="Compression: none, zip, or tgz.")] = "none",
    ) -> dict:
        """Export the PCB in ODB++ fabrication format (KiCad 9.0+).

        ## Return Format
        {"success": bool, "output": str, "data": {"path": str, "size_kb": float}}

        ## Examples
        await pcb_export_odbpp(file_name="esp32.kicad_pcb")
        await pcb_export_odbpp(file_name="esp32.kicad_pcb", compress="zip")
        """
        path = os.path.join(upload_dir, file_name) if not os.path.isabs(file_name) else file_name
        output_path = os.path.join(output_dir, output_name)
        args = ["pcb", "export", "odb", path, "--output", output_path]
        if compress != "none":
            args.extend(["--compress", compress])
        result = await run_kicad_cli(args)
        if result["success"]:
            if os.path.isfile(output_path):
                return {
                    "success": True,
                    "output": output_name,
                    "data": {"path": output_path, "size_kb": os.path.getsize(output_path) / 1024},
                }
            if os.path.isdir(output_path):
                files = sorted(os.listdir(output_path))
                return {
                    "success": True,
                    "output": output_name,
                    "data": {"dir": output_path, "files": files, "count": len(files)},
                }
            return {"success": True, "data": {"raw": result.get("stdout", "")}}
        return {
            "success": False,
            "message": result.get("stderr", "ODB++ export failed"),
            "output": output_name,
            "data": None,
        }

    # ── pcb_place_component ─────────────────────────────────────────────

    @mcp.tool(annotations=_MUTATING, version="0.1.0")
    async def pcb_place_component(
        library: Annotated[
            str, Field(description="Footprint library nickname (e.g. 'Resistor_SMD', 'Capacitor_SMD').")
        ],
        footprint: Annotated[str, Field(description="Footprint name (e.g. 'R_US_0603', 'C_0805').")],
        reference: Annotated[str, Field(description="Reference designator (e.g. 'R1', 'U2').")],
        value: Annotated[str, Field(description="Component value (e.g. '10k', '100nF').")] = "?",
        x_mm: Annotated[float, Field(description="X position in mm.", ge=-10000, le=10000)] = 0,
        y_mm: Annotated[float, Field(description="Y position in mm.", ge=-10000, le=10000)] = 0,
        rotation_deg: Annotated[float, Field(description="Rotation in degrees.", ge=0, le=360)] = 0,
        layer: Annotated[str, Field(description="Layer: F.Cu or B.Cu.")] = "F.Cu",
    ) -> dict:
        """Place a component footprint on the PCB.

        Loads a footprint from a KiCad library and places it at the given position.
        Requires TCP bridge (KiCad GUI with kc_bridge.py).

        ## Return Format
        {"success": bool, "data": {"reference": str, "footprint": str}}

        ## Examples
        await pcb_place_component(library="Resistor_SMD", footprint="R_US_0603", reference="R1", value="10k", x_mm=50, y_mm=30)
        """
        resp = await bridge_send(
            "pcb_place_component",
            {
                "library": library,
                "footprint": footprint,
                "reference": reference,
                "value": value,
                "position_mm": {"x": x_mm, "y": y_mm},
                "rotation_deg": rotation_deg,
                "layer": layer,
            },
        )
        return resp

    # ── pcb_add_track ──────────────────────────────────────────────────

    @mcp.tool(annotations=_MUTATING, version="0.1.0")
    async def pcb_add_track(
        start_x_mm: Annotated[float, Field(description="Track start X in mm.")] = 0,
        start_y_mm: Annotated[float, Field(description="Track start Y in mm.")] = 0,
        end_x_mm: Annotated[float, Field(description="Track end X in mm.")] = 10,
        end_y_mm: Annotated[float, Field(description="Track end Y in mm.")] = 10,
        layer: Annotated[str, Field(description="Layer name: F.Cu, B.Cu, etc.")] = "F.Cu",
        width_mm: Annotated[float, Field(description="Track width in mm.", gt=0)] = 0.25,
        net_name: Annotated[str, Field(description="Net name to assign (optional).")] = "",
    ) -> dict:
        """Add a track segment to the PCB.

        Creates a copper track between two points on the specified layer.
        Requires TCP bridge.

        ## Return Format
        {"success": bool, "data": {"type": str, "length_mm": float}}

        ## Examples
        await pcb_add_track(start_x_mm=50, start_y_mm=30, end_x_mm=60, end_y_mm=30, width_mm=0.25)
        """
        resp = await bridge_send(
            "pcb_add_track",
            {
                "start_mm": {"x": start_x_mm, "y": start_y_mm},
                "end_mm": {"x": end_x_mm, "y": end_y_mm},
                "layer": layer,
                "width_mm": width_mm,
                "net_name": net_name,
            },
        )
        return resp

    # ── pcb_add_via ────────────────────────────────────────────────────

    @mcp.tool(annotations=_MUTATING, version="0.1.0")
    async def pcb_add_via(
        x_mm: Annotated[float, Field(description="Via X position in mm.")] = 0,
        y_mm: Annotated[float, Field(description="Via Y position in mm.")] = 0,
        diameter_mm: Annotated[float, Field(description="Via pad diameter in mm.", gt=0)] = 0.6,
        drill_mm: Annotated[float, Field(description="Via drill hole diameter in mm.", gt=0)] = 0.3,
        net_name: Annotated[str, Field(description="Net name to assign (optional).")] = "",
    ) -> dict:
        """Add a through via to the PCB.

        Creates a plated through-hole via at the given position.
        Requires TCP bridge.

        ## Return Format
        {"success": bool, "data": {"x_mm": float, "y_mm": float, "diameter_mm": float}}

        ## Examples
        await pcb_add_via(x_mm=55, y_mm=30, diameter_mm=0.6, drill_mm=0.3)
        """
        resp = await bridge_send(
            "pcb_add_via",
            {
                "position_mm": {"x": x_mm, "y": y_mm},
                "diameter_mm": diameter_mm,
                "drill_mm": drill_mm,
                "net_name": net_name,
            },
        )
        return resp

    # ── pcb_save ───────────────────────────────────────────────────────

    @mcp.tool(annotations=_MUTATING, version="0.1.0")
    async def pcb_save(
        file_name: Annotated[
            str, Field(description="Output .kicad_pcb filename. Defaults to overwriting the loaded file.")
        ] = "",
    ) -> dict:
        """Save the current board to a .kicad_pcb file.

        Persists all in-memory changes (placed components, tracks, vias, board outline).
        Requires TCP bridge.

        ## Return Format
        {"success": bool, "data": {"path": str, "saved": bool}}

        ## Examples
        await pcb_save()
        await pcb_save(file_name="my_board_v2.kicad_pcb")
        """
        path = os.path.join(upload_dir, file_name) if file_name else ""
        resp = await bridge_send("pcb_save", {"path": path})
        return resp

    # ── pcb_set_board_outline ─────────────────────────────────────────

    @mcp.tool(annotations=_MUTATING, version="0.1.0")
    async def pcb_set_board_outline(
        points: Annotated[
            list, Field(description="List of {x, y} dicts defining the board edge polygon (min 3 points, in mm).")
        ],
    ) -> dict:
        """Set the PCB board outline (Edge.Cuts) from a list of points.

        Creates a closed polygon on the Edge.Cuts layer defining the board shape.
        Requires TCP bridge.

        ## Return Format
        {"success": bool, "data": {"vertices": int}}

        ## Examples
        await pcb_set_board_outline(points=[{"x": 0, "y": 0}, {"x": 100, "y": 0}, {"x": 100, "y": 80}, {"x": 0, "y": 80}])
        """
        resp = await bridge_send("pcb_set_board_outline", {"points": points})
        return resp

    # ── Return tool dict ───────────────────────────────────────────────

    return {
        "pcb_load": pcb_load,
        "pcb_info": pcb_info,
        "pcb_list_components": pcb_list_components,
        "pcb_list_nets": pcb_list_nets,
        "pcb_list_tracks": pcb_list_tracks,
        "pcb_get_component": pcb_get_component,
        "pcb_drc": pcb_drc,
        "pcb_export_step": pcb_export_step,
        "pcb_export_gerber": pcb_export_gerber,
        "pcb_export_pos": pcb_export_pos,
        "pcb_export_dxf": pcb_export_dxf,
        "pcb_export_svg": pcb_export_svg,
        "pcb_export_pdf": pcb_export_pdf,
        "pcb_export_vrml": pcb_export_vrml,
        "pcb_export_glb": pcb_export_glb,
        "pcb_export_ipc2581": pcb_export_ipc2581,
        "pcb_export_odbpp": pcb_export_odbpp,
        "pcb_place_component": pcb_place_component,
        "pcb_add_track": pcb_add_track,
        "pcb_add_via": pcb_add_via,
        "pcb_save": pcb_save,
        "pcb_set_board_outline": pcb_set_board_outline,
    }
