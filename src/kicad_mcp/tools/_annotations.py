"""Shared MCP tool-annotation constants.

Real MCP protocol fields (mcp.types.ToolAnnotations: readOnlyHint,
destructiveHint, idempotentHint, openWorldHint) -- not the {"readonly": True}
/ {"readonly": False, "mutating": True} shape this repo's tool modules had
been duplicating, which uses made-up keys ToolAnnotations doesn't recognize
and silently drops as unvalidated extra_data (confirmed by inspecting
mcp.types.ToolAnnotations directly; same bug found and fixed the same way
in database-operations-mcp). FastMCP accepts a plain dict here and coerces
it to ToolAnnotations, so these are ordinary dicts using the real field
names.
"""

READ_ONLY = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}
MUTATING = {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False}
DESTRUCTIVE = {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False}
