"""
KiCad MCP — PCB/schematic design automation via FastMCP 3.2 Unified Gateway.

Provides programmatic access to KiCad's pcbnew Python API for PCB manipulation,
schematic editing, BOM generation, library management, and cross-tool pipeline
with freecad-mcp for enclosure design.

Exports:
    kicad_status — server health and KiCad availability
    pcb_load — load a .kicad_pcb file
    pcb_info — board metadata (layers, dimensions, component count)
    pcb_list_components — list all components with footprints
    pcb_list_nets — list all nets with pad connections
    pcb_export_step — export board as STEP 3D model
    pcb_export_gerber — export Gerber manufacturing files
    pcb_drc — design rule check report
    sch_load — load .kicad_sch file
    sch_info — schematic metadata
    sch_erc — electrical rules check
    sch_export_netlist — export netlist
    bom_generate — generate BOM as CSV/JSON
    lib_search_footprint — search footprint libraries
    lib_list_libraries — list available symbol/footprint libraries
"""

from __future__ import annotations

import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("kicad-mcp")
