"""PyInstaller entry point - dual transport (MCP_PORT -> HTTP, fallback -> stdio)."""

import _datetime  # noqa: F401
import _strptime  # noqa: F401
import os
import sys

import mcp.types  # noqa: F401  -- freeze mcp bootstrap before fastmcp (PITFALLS §E)

sys.path.insert(0, ".")

port = os.environ.get("MCP_PORT") or os.environ.get("PORT")
if port:
    host = os.environ.get("MCP_HOST", "127.0.0.1")
    sys.argv = ["run_server.py", "--mode", "http", "--host", host, "--port", str(port)]

from kicad_mcp.server import main

main()
