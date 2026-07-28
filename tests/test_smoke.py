"""Smoke test for kicad-mcp server imports and tool registration."""


def test_import_package():
    """Ensure the kicad_mcp package imports cleanly."""
    from kicad_mcp import __doc__ as pkg_doc

    assert "KiCad" in pkg_doc


def test_import_server():
    """Ensure server module imports without KiCad dependencies."""
    from kicad_mcp.server import KICAD_CLI_PATH, WORK_DIR, app

    assert app is not None
    assert KICAD_CLI_PATH is not None
    assert WORK_DIR is not None


def test_import_tools():
    """Ensure all tool registration functions are importable."""
    from kicad_mcp.tools import register_bom_tools, register_library_tools, register_pcb_tools, register_schematic_tools

    assert callable(register_pcb_tools)
    assert callable(register_schematic_tools)
    assert callable(register_bom_tools)
    assert callable(register_library_tools)


def test_state_dict():
    """Verify initial state structure."""
    from kicad_mcp.server import _state

    assert isinstance(_state, dict)


def test_kicad_cli_config():
    """Verify kicad-cli path detection is reasonable."""
    from kicad_mcp.server import _find_kicad_cli

    path = _find_kicad_cli()
    # May be None if KiCad not installed — that's fine for CI
    if path:
        assert "kicad-cli" in path.lower()
