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

- Python: `just test` (pytest)
- E2E: `just e2e` (Playwright)
- All new tools should include smoke tests
