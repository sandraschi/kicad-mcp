"""
Schematics & Parts Marketplace MCP tools for KiCad.

Searches GitHub, Kitspace, and SnapEDA for KiCad projects,
reference designs, and component parts (footprints, symbols, 3D models).

Registered via register_marketplace_tools(mcp, **deps) — called from server.py.
"""

import io
import logging
import os
import zipfile
from typing import Annotated

import httpx
from pydantic import Field

logger = logging.getLogger("kicad-mcp.marketplace")

_READ_ONLY = {"readonly": True}
_MUTATING = {"readonly": False, "mutating": True}

GITHUB_API = "https://api.github.com"
GITHUB_HEADERS = {}
_gh_token = os.environ.get("GITHUB_TOKEN", os.environ.get("GH_TOKEN", ""))

if _gh_token:
    GITHUB_HEADERS["Authorization"] = f"Bearer {_gh_token}"

SNAPEDA_API = "https://api.snapeda.com/api/v1"
KITSPACE_API = "https://kitspace.org/projects.json"
COMPONENT_SEARCH_API = "https://componentsearchengine.com/api/v1"


def register_marketplace_tools(
    mcp,
    state: dict,
    run_kicad_cli,
    upload_dir: str,
    output_dir: str,
):
    """Register all marketplace MCP tools on the FastMCP instance."""

    # ── marketplace_search ───────────────────────────────────────────────

    @mcp.tool(annotations=_READ_ONLY, version="0.1.0")
    async def marketplace_search(
        source: Annotated[str, Field(description="Source: github, kitspace, snapeda, or all.")] = "all",
        query: Annotated[str, Field(description="Search query (e.g. 'STM32 breakout', 'audio amplifier').")] = "",
        topic: Annotated[
            str, Field(description="Filter by topic (GitHub only): kicad, esp32, arduino, pcb, etc.")
        ] = "kicad",
        limit: Annotated[int, Field(description="Max results per source.", ge=1, le=50)] = 15,
    ) -> dict:
        """Search for KiCad PCB/schematic projects and reference designs across sources.

        GitHub: finds repos containing .kicad_pcb or .kicad_sch files.
        Kitspace: finds open-source hardware projects with ready-to-order BOMs.
        SnapEDA: finds component footprints, symbols, and 3D models.

        ## Return Format
        {"success": bool, "source": str, "data": {"results": [...], "total": int}}

        ## Examples
        await marketplace_search(query="ESP32 dev board")
        await marketplace_search(source="github", query="audio DAC", topic="pcb")
        await marketplace_search(source="snapeda", query="STM32F103C8T6")
        """
        results = []

        if source in ("github", "all"):
            gh_results = await _search_github(query, topic, limit)
            results.extend(gh_results)

        if source in ("kitspace", "all"):
            ks_results = await _search_kitspace(query, limit)
            results.extend(ks_results)

        if source in ("snapeda", "all"):
            se_results = await _search_snapeda(query, limit)
            results.extend(se_results)

        return {
            "success": True,
            "source": source,
            "data": {"results": results, "total": len(results)},
        }

    # ── marketplace_categories ───────────────────────────────────────────

    @mcp.tool(annotations=_READ_ONLY, version="0.1.0")
    async def marketplace_categories(
        source: Annotated[str, Field(description="Source: github, kitspace, or snapeda.")] = "github",
    ) -> dict:
        """List available categories/topics for browsing a marketplace source.

        ## Return Format
        {"success": bool, "source": str, "data": {"categories": [{"id": str, "label": str}, ...]}}

        ## Examples
        await marketplace_categories(source="github")
        await marketplace_categories(source="kitspace")
        """
        if source == "github":
            topics = [
                {"id": "kicad", "label": "KiCad Projects"},
                {"id": "esp32", "label": "ESP32 Boards"},
                {"id": "arduino", "label": "Arduino Shields"},
                {"id": "stm32", "label": "STM32 Designs"},
                {"id": "audio", "label": "Audio / Amplifier"},
                {"id": "power-supply", "label": "Power Supply"},
                {"id": "rf", "label": "RF / Wireless"},
                {"id": "sensor", "label": "Sensor Boards"},
                {"id": "motor-driver", "label": "Motor Drivers"},
                {"id": "led", "label": "LED / Display"},
                {"id": "fpga", "label": "FPGA Boards"},
                {"id": "usb", "label": "USB / Interface"},
            ]
        elif source == "kitspace":
            topics = [
                {"id": "all", "label": "All Projects"},
                {"id": "popular", "label": "Popular"},
                {"id": "recent", "label": "Recently Added"},
            ]
        elif source == "snapeda":
            topics = [
                {"id": "connector", "label": "Connectors"},
                {"id": "passive", "label": "Passives (R, C, L)"},
                {"id": "diode", "label": "Diodes"},
                {"id": "transistor", "label": "Transistors"},
                {"id": "microcontroller", "label": "Microcontrollers"},
                {"id": "sensor", "label": "Sensors"},
                {"id": "power", "label": "Power Management"},
                {"id": "interface", "label": "Interface ICs"},
            ]
        else:
            return {"success": False, "message": f"Unknown source: {source}", "data": None}

        return {"success": True, "source": source, "data": {"categories": topics}}

    # ── marketplace_download ─────────────────────────────────────────────

    @mcp.tool(annotations=_MUTATING, version="0.1.0")
    async def marketplace_download(
        source: Annotated[str, Field(description="Source: github, kitspace, or snapeda.")],
        repo_name: Annotated[
            str,
            Field(
                description="Repository name (e.g. 'owner/repo') for GitHub, project slug for Kitspace, part number for SnapEDA."
            ),
        ] = "",
        branch: Annotated[str, Field(description="Git branch/tag (GitHub only).")] = "main",
    ) -> dict:
        """Download a KiCad project or component from a marketplace source.

        GitHub: downloads repo as ZIP, extracts .kicad_pcb/.kicad_sch files into uploads.
        Kitspace: downloads project KiCad files.
        SnapEDA: downloads component (footprint .kicad_mod + symbol .kicad_sym).

        ## Return Format
        {"success": bool, "data": {"files": [str, ...], "count": int}}

        ## Examples
        await marketplace_download(source="github", repo_name="espressif/esp-dev-kits")
        await marketplace_download(source="snapeda", repo_name="STM32F103C8T6")
        """
        if source == "github":
            return await _download_github(repo_name, branch, upload_dir)
        elif source == "kitspace":
            return await _download_kitspace(repo_name, upload_dir)
        elif source == "snapeda":
            return await _download_snapeda(repo_name, upload_dir)
        return {"success": False, "message": f"Unknown source: {source}", "data": None}

    # ── parts_search ─────────────────────────────────────────────────────

    @mcp.tool(annotations=_READ_ONLY, version="0.1.0")
    async def parts_search(
        query: Annotated[
            str, Field(description="Part number or description (e.g. 'LM358', 'STM32F103C8T6', '10uF 0805').")
        ],
        source: Annotated[str, Field(description="Source: snapeda, kicad_builtin, or all.")] = "all",
        limit: Annotated[int, Field(description="Max results.", ge=1, le=50)] = 20,
    ) -> dict:
        """Search for component parts across SnapEDA, KiCad's built-in libraries, and online repos.

        Returns matching parts with footprint, symbol, and 3D model availability.

        ## Return Format
        {"success": bool, "data": {"parts": [{"name": str, "footprint": str, "symbol": str, "source": str}, ...], "count": int}}

        ## Examples
        await parts_search(query="LM358")
        await parts_search(query="STM32F407VGT6", source="snapeda")
        """
        parts = []

        if source in ("snapeda", "all"):
            se_parts = await _search_snapeda_parts(query, limit)
            parts.extend(se_parts)

        if source in ("kicad_builtin", "all"):
            # Search KiCad's built-in libraries via kicad-cli
            fp_result = await run_kicad_cli(["pcb", "list-footprints", "--search", query, "--limit", str(limit // 2)])
            if fp_result["success"]:
                for line in fp_result.get("stdout", "").splitlines():
                    line = line.strip()
                    if line:
                        parts.append(
                            {
                                "name": line,
                                "source": "kicad_builtin",
                                "type": "footprint",
                                "availability": "built-in",
                            }
                        )

            sym_result = await run_kicad_cli(["sch", "list-symbols", "--search", query, "--limit", str(limit // 2)])
            if sym_result["success"]:
                for line in sym_result.get("stdout", "").splitlines():
                    line = line.strip()
                    if line:
                        parts.append(
                            {
                                "name": line,
                                "source": "kicad_builtin",
                                "type": "symbol",
                                "availability": "built-in",
                            }
                        )

        return {"success": True, "data": {"parts": parts[:limit], "count": min(len(parts), limit)}}

    # ── parts_missing ────────────────────────────────────────────────────

    @mcp.tool(annotations=_READ_ONLY, version="0.1.0")
    async def parts_missing(
        file_name: Annotated[str, Field(description="KiCad PCB filename to check.")],
    ) -> dict:
        """Check a PCB for components that lack footprints, symbols, or 3D models.

        ## Return Format
        {"success": bool, "data": {"missing_footprints": [str, ...], "missing_symbols": [str, ...], ...}}

        ## Examples
        await parts_missing(file_name="my_board.kicad_pcb")
        """
        path = os.path.join(upload_dir, file_name) if not os.path.isabs(file_name) else file_name
        if not os.path.isfile(path):
            return {"success": False, "message": f"File not found: {file_name}", "data": None}

        missing = {"missing_footprints": [], "missing_symbols": [], "missing_3d_models": []}

        try:
            # Parse the s-expr PCB file for component references and footprint assignments
            with open(path, encoding="utf-8") as f:
                content = f.read()

            import re

            # Find all footprint modules with their references
            footprint_pattern = re.findall(
                r'\(footprint\s+"([^"]*)"(?:.*?)\(attr\s+smd.*?\)\s*\(fp_text\s+reference\s+"([^"]*)"',
                content,
                re.DOTALL,
            )
            for fp_name, ref in footprint_pattern:
                if fp_name in ("", "missing", "???"):
                    missing["missing_footprints"].append(ref)

            # Find symbols with missing footprint field in schematic files
            # (requires .kicad_sch to be loaded — approximate via PCB)
            symbols_without_fp = re.findall(
                r'\(footprint\s*""\s*\(fp_text\s+reference\s+"([^"]*)"',
                content,
                re.DOTALL,
            )
            for ref in symbols_without_fp:
                if ref not in missing["missing_footprints"]:
                    missing["missing_footprints"].append(ref)

        except Exception as e:
            logger.warning("parts_missing parse error: %s", e)

        return {
            "success": True,
            "data": {
                "missing_footprints": missing["missing_footprints"][:50],
                "missing_symbols": missing["missing_symbols"][:50],
                "missing_3d_models": missing["missing_3d_models"][:50],
                "footprints_total": len(missing["missing_footprints"]),
            },
        }

    return {
        "marketplace_search": marketplace_search,
        "marketplace_categories": marketplace_categories,
        "marketplace_download": marketplace_download,
        "parts_search": parts_search,
        "parts_missing": parts_missing,
    }


# ── GitHub helpers ───────────────────────────────────────────────────────────


async def _search_github(query: str, topic: str, limit: int) -> list:
    """Search GitHub for KiCad projects via code search for .kicad_pcb files."""
    results = []
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            # Strategy 1: Search repos by topic
            q_parts = []
            if query:
                q_parts.append(query)
            if topic:
                q_parts.append(f"topic:{topic}")
            q_parts.append("kicad")  # ensure kicad-related

            q = " ".join(q_parts)
            url = f"{GITHUB_API}/search/repositories"
            headers = {**GITHUB_HEADERS, "Accept": "application/vnd.github.v3+json"}

            resp = await client.get(
                url, params={"q": q, "sort": "stars", "order": "desc", "per_page": limit}, headers=headers
            )
            if resp.status_code == 200:
                data = resp.json()
                for repo in data.get("items", []):
                    results.append(
                        {
                            "source": "github",
                            "type": "repository",
                            "name": repo["full_name"],
                            "description": repo.get("description", ""),
                            "url": repo["html_url"],
                            "clone_url": repo.get("clone_url", ""),
                            "stars": repo.get("stargazers_count", 0),
                            "language": repo.get("language", ""),
                            "topics": repo.get("topics", []),
                            "updated_at": repo.get("updated_at", ""),
                        }
                    )

            # Strategy 2: If few results, also code-search for actual .kicad_pcb files
            if len(results) < limit and query:
                code_url = f"{GITHUB_API}/search/code"
                code_resp = await client.get(
                    code_url,
                    params={"q": f"{query} extension:kicad_pcb", "per_page": limit - len(results)},
                    headers=headers,
                )
                if code_resp.status_code == 200:
                    code_data = code_resp.json()
                    seen = {r["name"] for r in results}
                    for item in code_data.get("items", []):
                        repo_name = item["repository"]["full_name"]
                        if repo_name not in seen:
                            seen.add(repo_name)
                            results.append(
                                {
                                    "source": "github",
                                    "type": "kicad_pcb_file",
                                    "name": repo_name,
                                    "description": f"Contains: {item['name']} ({item['path']})",
                                    "url": item["repository"]["html_url"],
                                    "file_url": item["html_url"],
                                    "stars": item["repository"].get("stargazers_count", 0),
                                }
                            )

    except Exception as e:
        logger.warning("GitHub search error: %s", e)
        results.append({"source": "github", "error": str(e)})

    return results


async def _download_github(repo_name: str, branch: str, upload_dir: str) -> dict:
    """Download GitHub repo ZIP and extract KiCad files."""
    if "/" not in repo_name:
        return {"success": False, "message": "Repo name must be 'owner/repo' format", "data": None}

    try:
        zip_url = f"https://github.com/{repo_name}/archive/refs/heads/{branch}.zip"
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            resp = await client.get(zip_url, headers=GITHUB_HEADERS)
            if resp.status_code != 200:
                return {"success": False, "message": f"GitHub returned {resp.status_code}", "data": None}

            # Extract KiCad files from ZIP
            kicad_files = []
            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                for name in zf.namelist():
                    basename = os.path.basename(name)
                    if basename.endswith((".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_mod", ".kicad_sym")):
                        dest = os.path.join(upload_dir, basename)
                        with zf.open(name) as src, open(dest, "wb") as dst:
                            dst.write(src.read())
                        kicad_files.append(basename)

            # Also extract any .pretty/ directories
            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                for name in zf.namelist():
                    if ".pretty/" in name and not name.endswith("/"):
                        dest = os.path.join(upload_dir, os.path.basename(name))
                        os.makedirs(os.path.dirname(dest), exist_ok=True)
                        with zf.open(name) as src, open(dest, "wb") as dst:
                            dst.write(src.read())

            return {
                "success": True,
                "data": {"repo": repo_name, "files": kicad_files, "count": len(kicad_files)},
            }
    except Exception as e:
        return {"success": False, "message": str(e), "data": None}


# ── Kitspace helpers ─────────────────────────────────────────────────────────


async def _search_kitspace(query: str, limit: int) -> list:
    """Search Kitspace for open-source hardware projects."""
    results = []
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(KITSPACE_API)
            if resp.status_code != 200:
                return results

            projects = resp.json()
            count = 0
            q_lower = query.lower() if query else ""

            for proj in projects.get("projects", []):
                if count >= limit:
                    break
                name = proj.get("name", "")
                summary = proj.get("summary", "")
                if q_lower and q_lower not in name.lower() and q_lower not in summary.lower():
                    continue
                results.append(
                    {
                        "source": "kitspace",
                        "type": "project",
                        "name": name,
                        "description": summary,
                        "url": f"https://kitspace.org/projects/{proj.get('id', '')}",
                        "bom_available": bool(proj.get("gerbers")),
                        "gerber_available": bool(proj.get("gerbers")),
                    }
                )
                count += 1
    except Exception as e:
        logger.warning("Kitspace search error: %s", e)

    return results


async def _download_kitspace(slug: str, upload_dir: str) -> dict:
    """Download KiCad files from a Kitspace project."""
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            # Try to fetch the project Gerber/PCB zip
            zip_url = f"https://kitspace.org/projects/{slug}/gerbers.zip"
            resp = await client.get(zip_url)
            if resp.status_code != 200:
                return {"success": False, "message": "No gerber files available for this project", "data": None}

            kicad_files = []
            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                for name in zf.namelist():
                    basename = os.path.basename(name)
                    if basename.endswith((".kicad_pcb", ".kicad_sch", ".gbr", ".drl")):
                        dest = os.path.join(upload_dir, basename)
                        with zf.open(name) as src, open(dest, "wb") as dst:
                            dst.write(src.read())
                        kicad_files.append(basename)

            return {"success": True, "data": {"files": kicad_files, "count": len(kicad_files)}}
    except Exception as e:
        return {"success": False, "message": str(e), "data": None}


# ── SnapEDA helpers ──────────────────────────────────────────────────────────


_snapeda_token = os.environ.get("SNAPEDA_API_KEY", os.environ.get("SNAPEDA_CLIENT_SECRET", ""))


async def _search_snapeda(query: str, limit: int) -> list:
    """Search SnapEDA for component parts."""
    results = []
    if not _snapeda_token:
        return [{"source": "snapeda", "error": "SNAPEDA_API_KEY not set. Get a free key at https://www.snapeda.com"}]

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{SNAPEDA_API}/parts/search",
                params={"q": query, "limit": limit},
                headers={"Authorization": f"Bearer {_snapeda_token}"},
            )
            if resp.status_code == 200:
                data = resp.json()
                for part in data.get("results", []):
                    results.append(
                        {
                            "source": "snapeda",
                            "type": "part",
                            "name": part.get("part_number", ""),
                            "manufacturer": part.get("manufacturer", ""),
                            "description": part.get("description", ""),
                            "url": part.get("url", ""),
                            "has_footprint": bool(part.get("footprint_url")),
                            "has_symbol": bool(part.get("symbol_url")),
                            "has_3d_model": bool(part.get("model_3d_url")),
                        }
                    )
    except Exception as e:
        logger.warning("SnapEDA search error: %s", e)

    return results


async def _search_snapeda_parts(query: str, limit: int) -> list:
    """Search SnapEDA for specific parts."""
    results = []
    if not _snapeda_token:
        return []

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{SNAPEDA_API}/parts/search",
                params={"q": query, "limit": limit},
                headers={"Authorization": f"Bearer {_snapeda_token}"},
            )
            if resp.status_code == 200:
                data = resp.json()
                for part in data.get("results", []):
                    results.append(
                        {
                            "name": part.get("part_number", ""),
                            "manufacturer": part.get("manufacturer", ""),
                            "description": part.get("description", ""),
                            "source": "snapeda",
                            "availability": "download",
                            "has_footprint": bool(part.get("footprint_url")),
                            "has_symbol": bool(part.get("symbol_url")),
                            "has_3d_model": bool(part.get("model_3d_url")),
                        }
                    )
    except Exception as e:
        logger.warning("SnapEDA parts search error: %s", e)

    return results


async def _download_snapeda(part_number: str, upload_dir: str) -> dict:
    """Download a component from SnapEDA."""
    if not _snapeda_token:
        return {
            "success": False,
            "message": "SNAPEDA_API_KEY not set. Get a free key at https://www.snapeda.com",
            "data": None,
        }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{SNAPEDA_API}/parts/{part_number}/download",
                headers={"Authorization": f"Bearer {_snapeda_token}"},
            )
            if resp.status_code != 200:
                return {"success": False, "message": f"SnapEDA returned {resp.status_code}", "data": None}

            # Response should be a ZIP with KiCad files
            files = []
            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                for name in zf.namelist():
                    basename = os.path.basename(name)
                    if basename.endswith((".kicad_mod", ".kicad_sym", ".step", ".wrl")):
                        dest = os.path.join(upload_dir, basename)
                        with zf.open(name) as src, open(dest, "wb") as dst:
                            dst.write(src.read())
                        files.append(basename)

            return {"success": True, "data": {"part_number": part_number, "files": files, "count": len(files)}}
    except Exception as e:
        return {"success": False, "message": str(e), "data": None}
