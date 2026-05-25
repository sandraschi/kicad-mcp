"""Entry point for PyInstaller-bundled server."""
import sys

sys.path.insert(0, ".")

from kicad_mcp.server import main

main()
