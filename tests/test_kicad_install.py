"""Tests for hybrid KiCad CLI discovery."""

from __future__ import annotations

from kicad_mcp.kicad_install import (
    KicadCliInstall,
    parse_crud_backend_pref,
    parse_ipc_enabled_pref,
    resolve_ipc_cli,
    resolve_stable_cli,
)


def test_parse_crud_backend_pref_defaults():
    assert parse_crud_backend_pref() == "auto"


def test_parse_ipc_enabled_pref_defaults():
    assert parse_ipc_enabled_pref() == "auto"


def test_resolve_stable_cli_missing(monkeypatch):
    monkeypatch.delenv("KICAD_CLI_PATH", raising=False)
    monkeypatch.setattr(
        "kicad_mcp.kicad_install.discover_cli_installs",
        lambda: [],
    )
    assert resolve_stable_cli() is None


def test_resolve_stable_cli_env_override(monkeypatch, tmp_path):
    cli = tmp_path / "kicad-cli.exe"
    cli.write_text("", encoding="utf-8")
    monkeypatch.setenv("KICAD_CLI_PATH", str(cli))
    monkeypatch.setattr("kicad_mcp.kicad_install._cli_version", lambda _p: "10.0.3")
    monkeypatch.setattr("kicad_mcp.kicad_install._has_api_server_subcommand", lambda _p: False)
    install = resolve_stable_cli()
    assert install is not None
    assert install.path == str(cli)
    assert install.major == 10


def test_resolve_ipc_cli_requires_api_server(monkeypatch, tmp_path):
    cli = tmp_path / "kicad-cli-nightly.exe"
    cli.write_text("", encoding="utf-8")
    monkeypatch.setenv("KICAD_IPC_CLI_PATH", str(cli))
    monkeypatch.setattr("kicad_mcp.kicad_install._cli_version", lambda _p: "11.0.0-rc1")
    monkeypatch.setattr("kicad_mcp.kicad_install._has_api_server_subcommand", lambda _p: False)
    assert resolve_ipc_cli() is None


def test_resolve_ipc_cli_picks_api_server(monkeypatch, tmp_path):
    stable = tmp_path / "stable.exe"
    nightly = tmp_path / "nightly.exe"
    stable.write_text("", encoding="utf-8")
    nightly.write_text("", encoding="utf-8")

    def fake_discover():
        return [
            KicadCliInstall(path=str(stable), version="10.0.3", major=10, has_api_server=False),
            KicadCliInstall(path=str(nightly), version="11.0.0-rc1", major=11, has_api_server=True),
        ]

    monkeypatch.delenv("KICAD_IPC_CLI_PATH", raising=False)
    monkeypatch.setattr("kicad_mcp.kicad_install.discover_cli_installs", fake_discover)
    install = resolve_ipc_cli()
    assert install is not None
    assert install.path == str(nightly)
    assert install.has_api_server is True
