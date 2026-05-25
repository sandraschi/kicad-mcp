"""
KiCad MCP tool modules — portmanteau re-exports.

Each submodule registers its tools via a register_* function that accepts
the FastMCP instance and server dependencies (pcbnew module, kicad-cli path,
work directories). Call all registration functions from server.py after mcp creation.
"""

from kicad_mcp.tools.bom import register_bom_tools
from kicad_mcp.tools.library import register_library_tools
from kicad_mcp.tools.marketplace import register_marketplace_tools
from kicad_mcp.tools.pcb import register_pcb_tools
from kicad_mcp.tools.schematic import register_schematic_tools

__all__ = [
    "register_bom_tools",
    "register_library_tools",
    "register_marketplace_tools",
    "register_pcb_tools",
    "register_schematic_tools",
]
