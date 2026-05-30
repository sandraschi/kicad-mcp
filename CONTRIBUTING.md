# Contributing

## How to Contribute

1. Fork the repo
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Make changes
4. Run `just lint` and `just test`
5. Commit with conventional commit format
6. Open a PR against `master`

## Development Setup

See [docs/SETUP.md](docs/SETUP.md) for full setup instructions.

## Code Standards

- Python: follow Ruff rules (see `pyproject.toml`)
- TypeScript: strict mode, Biome formatting
- Docstrings: SOTA protocol — `Annotated[T, Field(description="...")]`, no `Args:` blocks
- MCP tools: always include `annotations=` and `version=` on `@mcp.tool()`
- Tools that create/modify files: use `_MUTATING`
- Read-only tools: use `_READ_ONLY`

## Testing

- Python: `just test` (pytest — includes `test_kicad_install`, `test_crud_router`)
- Hybrid probe: `uv run python -m kicad_mcp.scripts.probe_ipc_headless`
- E2E: `just e2e` (Playwright)
- IPC changes: run probe + `kicad_status` after installing 11 nightly

## Hybrid KiCad development

When working on IPC/CRUD features:

1. `uv sync --extra ipc`
2. Install KiCad 11 nightly side-by-side with 10.0.x
3. Use board **copies** only
4. Document env vars in `docs/NIGHTLY_HEADLESS.md` and fleet `HYBRID_INSTALL.md`
