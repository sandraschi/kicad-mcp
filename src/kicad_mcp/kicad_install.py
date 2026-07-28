"""Discover stable vs nightly KiCad installs on Windows (hybrid headless path)."""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class KicadCliInstall:
    path: str
    version: str | None
    major: int | None
    has_api_server: bool


def _normalize(path: str) -> str:
    return str(Path(path))


def _parse_major(version_text: str | None) -> int | None:
    if not version_text:
        return None
    match = re.search(r"(\d+)\.", version_text.strip())
    if not match:
        return None
    return int(match.group(1))


def _cli_version(cli_path: str) -> str | None:
    try:
        result = subprocess.run(
            [cli_path, "version"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        text = (result.stdout or result.stderr or "").strip()
        return text.splitlines()[0].strip() if text else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def _has_api_server_subcommand(cli_path: str) -> bool:
    try:
        result = subprocess.run(
            [cli_path, "api-server", "--help"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        combined = f"{result.stdout}\n{result.stderr}".lower()
        return result.returncode == 0 and "api-server" in combined and "headless" in combined
    except (OSError, subprocess.TimeoutExpired):
        return False


def _windows_candidate_paths() -> list[str]:
    roots = [
        Path(r"C:\Program Files\KiCad"),
        Path(r"C:\Program Files (x86)\KiCad"),
    ]
    candidates: list[str] = []
    for root in roots:
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir(), reverse=True):
            cli = child / "bin" / "kicad-cli.exe"
            if cli.is_file():
                candidates.append(str(cli))
    # Explicit version pins (newest first for stable preference elsewhere)
    pinned = [
        r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe",
        r"C:\Program Files\KiCad\11.0\bin\kicad-cli.exe",
        r"C:\Program Files\KiCad\10.99\bin\kicad-cli.exe",
        r"C:\Program Files\KiCad\9.0\bin\kicad-cli.exe",
        r"C:\Program Files\KiCad\8.0\bin\kicad-cli.exe",
    ]
    for path in pinned:
        if os.path.isfile(path) and path not in candidates:
            candidates.append(path)
    return candidates


def _where_kicad_cli() -> str | None:
    try:
        result = subprocess.run(
            ["where", "kicad-cli"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().splitlines()[0].strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def discover_cli_installs() -> list[KicadCliInstall]:
    seen: set[str] = set()
    installs: list[KicadCliInstall] = []

    for raw in _windows_candidate_paths() + ([_where_kicad_cli()] if _where_kicad_cli() else []):
        if not raw or raw in seen or not os.path.isfile(raw):
            continue
        seen.add(raw)
        version = _cli_version(raw)
        installs.append(
            KicadCliInstall(
                path=_normalize(raw),
                version=version,
                major=_parse_major(version),
                has_api_server=_has_api_server_subcommand(raw),
            )
        )
    return installs


def resolve_stable_cli(explicit: str | None = None) -> KicadCliInstall | None:
    """Prefer KiCad 10.x stable for kicad-cli exports; env KICAD_CLI_PATH overrides."""
    if explicit and os.path.isfile(explicit):
        path = _normalize(explicit)
        version = _cli_version(path)
        return KicadCliInstall(
            path=path,
            version=version,
            major=_parse_major(version),
            has_api_server=_has_api_server_subcommand(path),
        )

    env = os.environ.get("KICAD_CLI_PATH", "").strip()
    if env and os.path.isfile(env):
        path = _normalize(env)
        version = _cli_version(path)
        return KicadCliInstall(
            path=path,
            version=version,
            major=_parse_major(version),
            has_api_server=_has_api_server_subcommand(path),
        )

    installs = discover_cli_installs()
    # Prefer highest major that does NOT expose api-server (true stable lane)
    stable = [i for i in installs if not i.has_api_server]
    if stable:
        stable.sort(key=lambda i: i.major or 0, reverse=True)
        return stable[0]

    # Fall back: any install without api-server by major<=10
    legacy = [i for i in installs if (i.major or 0) <= 10]
    if legacy:
        legacy.sort(key=lambda i: i.major or 0, reverse=True)
        return legacy[0]

    if installs:
        installs.sort(key=lambda i: i.major or 0, reverse=True)
        return installs[0]
    return None


def resolve_ipc_cli(explicit: str | None = None) -> KicadCliInstall | None:
    """Prefer KiCad 11 nightly (api-server) for headless IPC; env KICAD_IPC_CLI_PATH overrides."""
    if explicit and os.path.isfile(explicit):
        path = _normalize(explicit)
        version = _cli_version(path)
        install = KicadCliInstall(
            path=path,
            version=version,
            major=_parse_major(version),
            has_api_server=_has_api_server_subcommand(path),
        )
        return install if install.has_api_server else None

    env = os.environ.get("KICAD_IPC_CLI_PATH", "").strip()
    if env and os.path.isfile(env):
        path = _normalize(env)
        version = _cli_version(path)
        install = KicadCliInstall(
            path=path,
            version=version,
            major=_parse_major(version),
            has_api_server=_has_api_server_subcommand(path),
        )
        return install if install.has_api_server else None

    installs = [i for i in discover_cli_installs() if i.has_api_server]
    if not installs:
        return None
    installs.sort(key=lambda i: i.major or 0, reverse=True)
    return installs[0]


def ipc_python_available() -> bool:
    try:
        import kipy  # noqa: F401

        return True
    except ImportError:
        return False


def parse_crud_backend_pref() -> str:
    raw = os.environ.get("KICAD_MCP_CRUD_BACKEND", "auto").strip().lower()
    if raw in {"auto", "ipc", "tcp", "none"}:
        return raw
    return "auto"


def parse_ipc_enabled_pref() -> str:
    raw = os.environ.get("KICAD_MCP_IPC_ENABLED", "auto").strip().lower()
    if raw in {"auto", "1", "true", "yes", "0", "false", "no"}:
        return raw
    return "auto"


def ipc_enabled() -> bool:
    pref = parse_ipc_enabled_pref()
    if pref in {"0", "false", "no"}:
        return False
    if pref in {"1", "true", "yes"}:
        return True
    return True  # auto: caller checks resolve_ipc_cli + kipy
