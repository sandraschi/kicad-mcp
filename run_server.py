"""PyInstaller entry point — dual transport (MCP_PORT → HTTP, fallback → stdio)."""
import os
import _strptime  # noqa: F401
import sys

sys.path.insert(0, ".")

port = os.environ.get("MCP_PORT") or os.environ.get("PORT")
if port:
    host = os.environ.get("MCP_HOST", "127.0.0.1")
    sys.argv = ["run_server.py", "--mode", "http", "--host", host, "--port", str(port)]

from kicad_mcp.server import main

main()

