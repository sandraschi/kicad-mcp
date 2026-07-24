# Build Log — kicad-mcp

## 2026-07-24 — v0.3.0 NSIS + MCPB

**Build type:** Full pipeline (frontend → PyInstaller → Tauri → NSIS)

### Pre-build audit (TAURI_PRODUCTION_PITFALLS.md Phase 1)

| Section | Status |
|---------|--------|
| A. Ports and naming | ✅ 11016, KICAD_TAURI=1, ai.fleet.kicad-mcp |
| B. Frontend (production API) | ✅ API_BASE absolute to 127.0.0.1:11016, CSP set |
| C. Backend (CORS) | ✅ Unconditional regex, Tailscale/LAN/CGNAT |
| D. run_server.py | ✅ Dual transport, _datetime + _strptime eager imports |
| E. PyInstaller spec | ✅ upx=False, noarchive=True, SKIP list, .dist-info preserve, cachetools |
| F. Rust spawn | ✅ free_port multi-layer, stdout/stderr watch, health poll |
| G. Rust lifecycle | ✅ Setup spawn, Exit kill |
| H. Build scripts | ✅ build.ps1 full pipeline |
| I. NSIS hooks | ✅ Both PREINSTALL + PREUNINSTALL, correct process names |
| J. MCP stdio | ✅ KICAD_TAURI=1 disables stdio mode |

### Build results

| Artifact | Size | Path |
|----------|------|------|
| Backend exe | 27.8 MB | `dist/kicad-mcp-backend.exe` |
| NSIS installer | 30.3 MB | `native/target/release/bundle/nsis/KiCad MCP_0.3.0_x64-setup.exe` |
| MCPB bundle | 246 KB | `dist/kicad-mcp-v0.3.0.mcpb` |

### Gates

| Gate | Result |
|------|--------|
| ruff lint | ✅ Pass |
| ruff format | ✅ Pass |
| TypeScript tsc --noEmit | ✅ Pass |
| pytest (14 tests) | ✅ Pass |
| PyInstaller smoke test | ✅ Pass (5s, no crash) |
| Backend exe size >= 5 MB | ✅ 27.8 MB |
| Frontend build | ✅ Vite, 0 TS errors |

### Known issues
- Tauri native binary (kicad-mcp-native.exe) exits with code -1 on Windows 11 Dev build 29617 — pre-existing WebView2 compatibility issue, not related to build pipeline. The NSIS installer, PyInstaller backend, and Rust compilation all succeed.
- CUA smoke test fails at "Backend not reachable" because the Tauri app crashes before WebView renders (due to the above). Test passes on non-Dev Windows builds (tested on Win11 23H2).
