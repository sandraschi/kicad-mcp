# kicad-mcp (MCPB Bundle)

KiCad MCP server — PCB/schematic design automation via MCP tools and REST API

## Usage

Add to \claude_desktop_config.json\:
\\\json
{
  "mcpServers": {
    "kicad-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "\D:\Dev\repos", "python", "-m", "kicad_mcp"],
      "env": { "PYTHONPATH": "\D:\Dev\repos/src" }
    }
  }
}
\\\

## Tools

- **kicad-mcp**: KiCad MCP server — PCB/schematic design automation via MCP tools and REST API

## Requirements

- Python 3.12+
- uv
