"""Tests for schematic mutation operations (sch_edit.py).

Uses minimal, self-contained fixture schematic and symbol-library content
(not a dependency on a real KiCad install) so these run in CI, where KiCad
is not installed. The fixture symbol content is structurally the same shape
as KiCad 10.0's real Device.kicad_sym "R" entry (verified by hand against
the installed library while building this module), just trimmed to the
fields sch_edit.py actually reads.
"""

from __future__ import annotations

from kicad_mcp.sch_edit import (
    _split_reference,
    add_component,
    add_label,
    add_wire,
    annotate,
    load_library_symbol,
    project_name_for,
    resolve_symbols_dir,
    root_uuid,
)
from kicad_mcp.sch_sexpr import find_child, find_children, parse, serialize_file, unquote

_MINIMAL_SCH = """(kicad_sch
\t(version 20250114)
\t(generator "eeschema")
\t(uuid "11111111-1111-1111-1111-111111111111")
\t(paper "A4")
\t(sheet_instances
\t\t(path "/"
\t\t\t(page "1")
\t\t)
\t)
\t(embedded_fonts no)
)
"""

_MINIMAL_DEVICE_SYM = """(kicad_symbol_lib
\t(version 20241209)
\t(generator "kicad_symbol_editor")
\t(symbol "R"
\t\t(pin_numbers
\t\t\t(hide yes)
\t\t)
\t\t(property "Reference" "R"
\t\t\t(at 2.032 0 90)
\t\t)
\t\t(property "Value" "R"
\t\t\t(at 0 0 90)
\t\t)
\t\t(symbol "R_1_1"
\t\t\t(pin passive line
\t\t\t\t(at 0 3.81 270)
\t\t\t\t(length 1.27)
\t\t\t\t(name ""
\t\t\t\t\t(effects (font (size 1.27 1.27)))
\t\t\t\t)
\t\t\t\t(number "1"
\t\t\t\t\t(effects (font (size 1.27 1.27)))
\t\t\t\t)
\t\t\t)
\t\t\t(pin passive line
\t\t\t\t(at 0 -3.81 90)
\t\t\t\t(length 1.27)
\t\t\t\t(name ""
\t\t\t\t\t(effects (font (size 1.27 1.27)))
\t\t\t\t)
\t\t\t\t(number "2"
\t\t\t\t\t(effects (font (size 1.27 1.27)))
\t\t\t\t)
\t\t\t)
\t\t)
\t)
)
"""


def _fixture_tree():
    return parse(_MINIMAL_SCH)


def test_root_uuid():
    tree = _fixture_tree()
    assert root_uuid(tree) == "11111111-1111-1111-1111-111111111111"


def test_project_name_for_no_pro_file(tmp_path):
    sch = tmp_path / "test.kicad_sch"
    sch.write_text(_MINIMAL_SCH, encoding="utf-8")
    assert project_name_for(str(sch)) == ""


def test_project_name_for_with_pro_file(tmp_path):
    sch = tmp_path / "myproject.kicad_sch"
    (tmp_path / "myproject.kicad_pro").write_text("{}", encoding="utf-8")
    sch.write_text(_MINIMAL_SCH, encoding="utf-8")
    assert project_name_for(str(sch)) == "myproject"


def test_add_wire_creates_valid_node():
    tree = _fixture_tree()
    wire_uuid = add_wire(tree, 10, 20, 30, 40, width=0.15)
    wires = find_children(tree, "wire")
    assert len(wires) == 1
    pts = find_child(wires[0], "pts")
    assert pts == ["pts", ["xy", "10", "20"], ["xy", "30", "40"]]
    uuid_node = find_child(wires[0], "uuid")
    assert uuid_node is not None
    assert unquote(uuid_node[1]) == wire_uuid


def test_add_wire_inserted_before_trailer():
    tree = _fixture_tree()
    add_wire(tree, 0, 0, 10, 10)
    heads = [c[0] for c in tree if isinstance(c, list)]
    assert heads.index("wire") < heads.index("sheet_instances")


def test_add_label_local():
    tree = _fixture_tree()
    label_uuid = add_label(tree, "NET1", 5, 5, kind="local")
    labels = find_children(tree, "label")
    assert len(labels) == 1
    assert unquote(labels[0][1]) == "NET1"
    uuid_node = find_child(labels[0], "uuid")
    assert uuid_node is not None
    assert unquote(uuid_node[1]) == label_uuid


def test_add_label_global_has_shape():
    tree = _fixture_tree()
    add_label(tree, "VCC", 5, 5, kind="global", shape="output")
    globals_ = find_children(tree, "global_label")
    assert len(globals_) == 1
    assert find_child(globals_[0], "shape") == ["shape", "output"]


def test_add_label_invalid_kind_raises():
    tree = _fixture_tree()
    try:
        add_label(tree, "X", 0, 0, kind="bogus")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_add_label_invalid_shape_raises():
    tree = _fixture_tree()
    try:
        add_label(tree, "X", 0, 0, kind="global", shape="bogus")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_load_library_symbol_renames_to_full_lib_id(tmp_path):
    (tmp_path / "Device.kicad_sym").write_text(_MINIMAL_DEVICE_SYM, encoding="utf-8")
    sym = load_library_symbol(str(tmp_path), "Device:R")
    assert unquote(sym[1]) == "Device:R"
    # sub-unit names stay short, matching real KiCad-written files
    sub_names = [unquote(s[1]) for s in find_children(sym, "symbol")]
    assert "R_1_1" in sub_names


def test_load_library_symbol_missing_library_raises(tmp_path):
    try:
        load_library_symbol(str(tmp_path), "Device:R")
        raise AssertionError("expected FileNotFoundError")
    except FileNotFoundError:
        pass


def test_load_library_symbol_missing_entry_raises(tmp_path):
    (tmp_path / "Device.kicad_sym").write_text(_MINIMAL_DEVICE_SYM, encoding="utf-8")
    try:
        load_library_symbol(str(tmp_path), "Device:NoSuchPart")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_add_component_places_symbol_with_correct_pin_count(tmp_path):
    (tmp_path / "Device.kicad_sym").write_text(_MINIMAL_DEVICE_SYM, encoding="utf-8")
    sch_path = tmp_path / "test.kicad_sch"
    tree = _fixture_tree()

    sym_uuid, ref = add_component(tree, str(sch_path), "Device:R", 10, 20, str(tmp_path), reference="R?", value="10k")
    assert ref == "R?"

    symbols = find_children(tree, "symbol")
    assert len(symbols) == 1
    placed = symbols[0]
    uuid_node = find_child(placed, "uuid")
    assert uuid_node is not None
    assert unquote(uuid_node[1]) == sym_uuid
    pins = find_children(placed, "pin")
    assert len(pins) == 2  # R has 2 pins per the fixture library
    assert {unquote(p[1]) for p in pins} == {"1", "2"}


def test_add_component_embeds_lib_symbols_once_for_repeated_placements(tmp_path):
    (tmp_path / "Device.kicad_sym").write_text(_MINIMAL_DEVICE_SYM, encoding="utf-8")
    sch_path = tmp_path / "test.kicad_sch"
    tree = _fixture_tree()

    add_component(tree, str(sch_path), "Device:R", 0, 0, str(tmp_path), reference="R?")
    add_component(tree, str(sch_path), "Device:R", 10, 0, str(tmp_path), reference="R?")

    lib_symbols = find_child(tree, "lib_symbols")
    assert lib_symbols is not None
    device_r_defs = [s for s in find_children(lib_symbols, "symbol") if unquote(s[1]) == "Device:R"]
    assert len(device_r_defs) == 1  # embedded once, referenced by both instances

    symbols = find_children(tree, "symbol")
    assert len(symbols) == 2


def test_annotate_assigns_sequential_and_skips_collisions(tmp_path):
    (tmp_path / "Device.kicad_sym").write_text(_MINIMAL_DEVICE_SYM, encoding="utf-8")
    sch_path = tmp_path / "test.kicad_sch"
    tree = _fixture_tree()

    # Place three R? placeholders, then manually assign a real reference to
    # simulate an existing R1 already present before annotate() runs.
    add_component(tree, str(sch_path), "Device:R", 0, 0, str(tmp_path), reference="R1", value="1k")
    add_component(tree, str(sch_path), "Device:R", 10, 0, str(tmp_path), reference="R?", value="2k")
    add_component(tree, str(sch_path), "Device:R", 20, 0, str(tmp_path), reference="R?", value="3k")

    changes = annotate(tree)
    assigned = sorted(new for _old, new in changes)
    assert assigned == ["R2", "R3"]  # R1 already used, never reassigned or collided with


def test_annotate_no_changes_when_all_assigned(tmp_path):
    (tmp_path / "Device.kicad_sym").write_text(_MINIMAL_DEVICE_SYM, encoding="utf-8")
    sch_path = tmp_path / "test.kicad_sch"
    tree = _fixture_tree()
    add_component(tree, str(sch_path), "Device:R", 0, 0, str(tmp_path), reference="R1")
    assert annotate(tree) == []


def test_split_reference_assigned():
    assert _split_reference("R4") == ("R", 4)
    assert _split_reference("U12") == ("U", 12)


def test_split_reference_placeholder():
    assert _split_reference("R?") == ("R", None)
    assert _split_reference("R") == ("R", None)


def test_resolve_symbols_dir_none_for_missing_path():
    assert resolve_symbols_dir(None) is None


def test_resolve_symbols_dir_none_for_nonexistent_install(tmp_path):
    fake_cli = tmp_path / "bin" / "kicad-cli.exe"
    fake_cli.parent.mkdir()
    fake_cli.write_text("", encoding="utf-8")
    assert resolve_symbols_dir(str(fake_cli)) is None  # share/kicad/symbols doesn't exist under tmp_path


def test_resolve_symbols_dir_finds_real_layout(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    cli = bin_dir / "kicad-cli.exe"
    cli.write_text("", encoding="utf-8")
    symbols_dir = tmp_path / "share" / "kicad" / "symbols"
    symbols_dir.mkdir(parents=True)
    assert resolve_symbols_dir(str(cli)) == str(symbols_dir)


def test_full_edit_serializes_and_reparses_cleanly(tmp_path):
    """Sanity check: a tree with every mutation type still round-trips through parse."""
    (tmp_path / "Device.kicad_sym").write_text(_MINIMAL_DEVICE_SYM, encoding="utf-8")
    sch_path = tmp_path / "test.kicad_sch"
    tree = _fixture_tree()

    add_wire(tree, 0, 0, 10, 0)
    add_label(tree, "NET1", 0, 0, kind="local")
    add_component(tree, str(sch_path), "Device:R", 5, 5, str(tmp_path), reference="R?")
    annotate(tree)

    out = serialize_file(tree)
    reparsed = parse(out)
    assert reparsed == tree
