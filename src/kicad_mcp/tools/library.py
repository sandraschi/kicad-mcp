"""
Library MCP tools for KiCad.

Provides footprint and symbol library search, listing, and inspection.
Uses kicad-cli for library queries.

Registered via register_library_tools(mcp, **deps) — called from server.py.
"""

import json
import logging
import os
from typing import Annotated

from pydantic import Field

logger = logging.getLogger("kicad-mcp.library")

_READ_ONLY = {"readonly": True}
_MUTATING = {"readonly": False, "mutating": True}


def register_library_tools(
    mcp,
    state: dict,
    run_kicad_cli,
    output_dir: str,
):
    """Register all Library MCP tools on the FastMCP instance."""

    # ── lib_list_footprints ─────────────────────────────────────────────

    @mcp.tool(annotations=_READ_ONLY, version="0.1.0")
    async def lib_list_footprints(
        library: Annotated[
            str,
            Field(
                description="Footprint library name (e.g. 'Capacitor_SMD', 'Resistor_SMD'). Empty = list all libraries."
            ),
        ] = "",
        search: Annotated[str, Field(description="Filter footprints by name substring.")] = "",
        limit: Annotated[int, Field(description="Max results.", ge=1, le=200)] = 50,
    ) -> dict:
        """List available footprints, optionally filtered by library and search term.

        ## Return Format
        {"success": bool, "data": {"footprints": [str, ...], "count": int}}

        ## Examples
        await lib_list_footprints(library="Capacitor_SMD")
        await lib_list_footprints(search="0805", limit=20)
        """
        args = ["pcb", "list-footprints"]
        if library:
            args.extend(["--lib", library])
        if search:
            args.extend(["--search", search])
        args.extend(["--limit", str(limit)])

        output_path = os.path.join(output_dir, "footprints.json")
        args.extend(["--output", output_path])

        result = await run_kicad_cli(args)
        if result["success"] and os.path.isfile(output_path):
            with open(output_path) as f:
                data = json.load(f)
            footprints = data if isinstance(data, list) else data.get("footprints", [])
            return {"success": True, "data": {"footprints": footprints, "count": len(footprints)}}
        return {"success": True, "data": {"footprints": result.get("stdout", "").splitlines(), "count": 0, "raw": True}}

    # ── lib_list_symbols ────────────────────────────────────────────────

    @mcp.tool(annotations=_READ_ONLY, version="0.1.0")
    async def lib_list_symbols(
        library: Annotated[str, Field(description="Symbol library name. Empty = list all libraries.")] = "",
        search: Annotated[str, Field(description="Filter symbols by name substring.")] = "",
        limit: Annotated[int, Field(description="Max results.", ge=1, le=200)] = 50,
    ) -> dict:
        """List available schematic symbols, optionally filtered.

        ## Return Format
        {"success": bool, "data": {"symbols": [str, ...], "count": int}}

        ## Examples
        await lib_list_symbols(library="Device")
        await lib_list_symbols(search="STM32", limit=30)
        """
        args = ["sch", "list-symbols"]
        if library:
            args.extend(["--lib", library])
        if search:
            args.extend(["--search", search])
        args.extend(["--limit", str(limit)])

        output_path = os.path.join(output_dir, "symbols.json")
        args.extend(["--output", output_path])

        result = await run_kicad_cli(args)
        if result["success"] and os.path.isfile(output_path):
            with open(output_path) as f:
                data = json.load(f)
            symbols = data if isinstance(data, list) else data.get("symbols", [])
            return {"success": True, "data": {"symbols": symbols, "count": len(symbols)}}
        return {"success": True, "data": {"symbols": result.get("stdout", "").splitlines(), "count": 0, "raw": True}}

    # ── lib_find_footprint ──────────────────────────────────────────────

    @mcp.tool(annotations=_READ_ONLY, version="0.1.0")
    async def lib_find_footprint(
        query: Annotated[str, Field(description="Footprint search query (e.g. 'SOIC-8', '0805', 'USB-C').")],
        limit: Annotated[int, Field(description="Max results.", ge=1, le=100)] = 20,
    ) -> dict:
        """Search for a specific footprint across all libraries.

        Returns matching footprint names with their library paths.

        ## Return Format
        {"success": bool, "data": {"results": [{"name": str, "library": str}, ...], "count": int}}

        ## Examples
        await lib_find_footprint(query="SOIC-8")
        await lib_find_footprint(query="USB Type-C receptacle")
        """
        args = ["pcb", "list-footprints", "--search", query, "--limit", str(limit)]
        output_path = os.path.join(output_dir, "footprint_search.json")
        args.extend(["--output", output_path])

        result = await run_kicad_cli(args)
        if result["success"] and os.path.isfile(output_path):
            with open(output_path) as f:
                data = json.load(f)
            results = data if isinstance(data, list) else data.get("footprints", [])
            return {"success": True, "data": {"results": results, "count": len(results)}}
        return {"success": False, "message": "Footprint search failed", "data": None}

    # ── lib_find_symbol ─────────────────────────────────────────────────

    @mcp.tool(annotations=_READ_ONLY, version="0.1.0")
    async def lib_find_symbol(
        query: Annotated[str, Field(description="Symbol search query (e.g. 'STM32F103', 'LM358', 'NE555').")],
        limit: Annotated[int, Field(description="Max results.", ge=1, le=100)] = 20,
    ) -> dict:
        """Search for a specific schematic symbol across all libraries.

        ## Return Format
        {"success": bool, "data": {"results": [{"name": str, "library": str}, ...], "count": int}}

        ## Examples
        await lib_find_symbol(query="STM32F103C8T6")
        """
        args = ["sch", "list-symbols", "--search", query, "--limit", str(limit)]
        output_path = os.path.join(output_dir, "symbol_search.json")
        args.extend(["--output", output_path])

        result = await run_kicad_cli(args)
        if result["success"] and os.path.isfile(output_path):
            with open(output_path) as f:
                data = json.load(f)
            results = data if isinstance(data, list) else data.get("symbols", [])
            return {"success": True, "data": {"results": results, "count": len(results)}}
        return {"success": False, "message": "Symbol search failed", "data": None}

    # ── fp_export_svg ───────────────────────────────────────────────────

    @mcp.tool(annotations=_MUTATING, version="0.1.0")
    async def fp_export_svg(
        footprint: Annotated[
            str, Field(description="Footprint name (e.g. 'R_US_0603'). Use library:name format or just name.")
        ],
        library: Annotated[
            str, Field(description="Library nickname (e.g. 'Resistor_SMD'). Optional if footprint is fully qualified.")
        ] = "",
        output_name: Annotated[str, Field(description="Output SVG filename.")] = "footprint.svg",
    ) -> dict:
        """Export a footprint as SVG.

        ## Return Format
        {"success": bool, "output": str, "data": {"path": str, "size_kb": float}}

        ## Examples
        await fp_export_svg(footprint="R_US_0603", library="Resistor_SMD")
        """
        output_path = os.path.join(output_dir, output_name)
        args = ["fp", "export", "svg", "--output", output_path]
        if library:
            args.extend(["--library", library])
        args.append(footprint)
        result = await run_kicad_cli(args)
        if result["success"] and os.path.isfile(output_path):
            return {
                "success": True,
                "output": output_name,
                "data": {"path": output_path, "size_kb": os.path.getsize(output_path) / 1024},
            }
        return {
            "success": False,
            "message": result.get("stderr", "Footprint SVG export failed"),
            "output": output_name,
            "data": None,
        }

    # ── sym_export_svg ──────────────────────────────────────────────────

    @mcp.tool(annotations=_MUTATING, version="0.1.0")
    async def sym_export_svg(
        symbol: Annotated[str, Field(description="Symbol name (e.g. 'LM358'). Use library:name format or just name.")],
        library: Annotated[
            str, Field(description="Library nickname (e.g. 'Device'). Optional if symbol is fully qualified.")
        ] = "",
        output_name: Annotated[str, Field(description="Output SVG filename.")] = "symbol.svg",
    ) -> dict:
        """Export a schematic symbol as SVG.

        ## Return Format
        {"success": bool, "output": str, "data": {"path": str, "size_kb": float}}

        ## Examples
        await sym_export_svg(symbol="LM358", library="Amplifier_Operational")
        """
        output_path = os.path.join(output_dir, output_name)
        args = ["sym", "export", "svg", "--output", output_path]
        if library:
            args.extend(["--library", library])
        args.append(symbol)
        result = await run_kicad_cli(args)
        if result["success"] and os.path.isfile(output_path):
            return {
                "success": True,
                "output": output_name,
                "data": {"path": output_path, "size_kb": os.path.getsize(output_path) / 1024},
            }
        return {
            "success": False,
            "message": result.get("stderr", "Symbol SVG export failed"),
            "output": output_name,
            "data": None,
        }

    return {
        "lib_list_footprints": lib_list_footprints,
        "lib_list_symbols": lib_list_symbols,
        "lib_find_footprint": lib_find_footprint,
        "lib_find_symbol": lib_find_symbol,
        "fp_export_svg": fp_export_svg,
        "sym_export_svg": sym_export_svg,
    }
