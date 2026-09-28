"""Schematic mutation operations: add wire/label/component, annotate references.

KiCad's own IPC API (kicad-python / kipy) does not expose schematic CRUD yet
-- confirmed by hands-on testing of kicad-python 0.7.1 and 0.8.0, both of
which fail to import their own `schematic` module (a version skew between
the pure-Python wrapper and its bundled protobuf definitions), and by
docs/NIGHTLY_HEADLESS.md's own compatibility table, which lists "Schematic
CRUD: not in IPC yet - export-only CLI". This module works around that by
editing .kicad_sch files directly as S-expression text via sch_sexpr.py,
the same approach standalone tools like kicad-skip use. See that module's
docstring for the round-trip fidelity tradeoff this implies.

Every function here takes an already-parsed tree (see sch_sexpr.parse) and
mutates it in place, returning identifying info about what was added/changed.
Callers are responsible for re-serializing and writing the file, and should
write to a fresh file only after validating (see tools/schematic.py, which
runs `kicad-cli sch erc` on the result before treating a write as successful).
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from kicad_mcp.sch_sexpr import find_child, find_children, parse, quote, unquote

# Reference-designator prefix per common device category, used by annotate().
# Not exhaustive -- symbols whose prefix isn't in this table keep whatever
# prefix their existing/placeholder reference already uses.
_KNOWN_PREFIXES = {
    "R": "R",
    "C": "C",
    "L": "L",
    "U": "U",
    "Q": "Q",
    "D": "D",
    "J": "J",
    "SW": "SW",
    "Y": "Y",
    "FB": "FB",
    "F": "F",
    "TP": "TP",
}


def new_uuid() -> str:
    return str(uuid.uuid4())


def root_uuid(tree: list) -> str:
    """The schematic's own uuid -- used as the instance path root ('/<uuid>')."""
    node = find_child(tree, "uuid")
    if node is None or len(node) < 2:
        raise ValueError("Schematic has no top-level (uuid ...) -- malformed file")
    return unquote(node[1])


def project_name_for(sch_path: str) -> str:
    """Best-effort project name: the .kicad_pro sibling file's stem, else ''."""
    folder = Path(sch_path).parent
    pro_files = list(folder.glob("*.kicad_pro"))
    if pro_files:
        return pro_files[0].stem
    return ""


def _insert_before_trailer(tree: list, node: list) -> None:
    """Insert a new top-level content node before sheet_instances/embedded_fonts.

    KiCad always writes sheet_instances and embedded_fonts last; every real
    file inspected while building this module follows that order, and
    KiCad's parser doesn't require any particular position for content nodes
    otherwise, but keeping the conventional trailer last avoids surprising a
    human who next opens the file in the KiCad GUI.
    """
    trailer_heads = {"sheet_instances", "embedded_fonts"}
    insert_at = len(tree)
    for i, child in enumerate(tree):
        if isinstance(child, list) and child and isinstance(child[0], str) and unquote(child[0]) in trailer_heads:
            insert_at = i
            break
    tree.insert(insert_at, node)


def add_wire(tree: list, x1: float, y1: float, x2: float, y2: float, width: float = 0.0) -> str:
    """Add a wire segment. Returns the new wire's uuid."""
    wire_uuid = new_uuid()
    node = [
        "wire",
        ["pts", ["xy", _num(x1), _num(y1)], ["xy", _num(x2), _num(y2)]],
        ["stroke", ["width", _num(width)], ["type", "default"]],
        ["uuid", quote(wire_uuid)],
    ]
    _insert_before_trailer(tree, node)
    return wire_uuid


_LABEL_KINDS = {"local": "label", "global": "global_label", "hierarchical": "hierarchical_label"}
_VALID_SHAPES = {"input", "output", "bidirectional", "tri_state", "passive"}


def add_label(
    tree: list,
    text: str,
    x: float,
    y: float,
    angle: float = 0.0,
    kind: str = "local",
    shape: str = "input",
) -> str:
    """Add a local/global/hierarchical label. Returns the new label's uuid.

    `kind` selects the token: "local" -> (label ...), "global" -> (global_label
    ...), "hierarchical" -> (hierarchical_label ...). `shape` only applies to
    global/hierarchical labels (per the KiCad file format spec's Label and
    Pin Shapes table) and is ignored for local labels.
    """
    if kind not in _LABEL_KINDS:
        raise ValueError(f"kind must be one of {sorted(_LABEL_KINDS)}, got {kind!r}")
    if kind != "local" and shape not in _VALID_SHAPES:
        raise ValueError(f"shape must be one of {sorted(_VALID_SHAPES)}, got {shape!r}")

    label_uuid = new_uuid()
    token = _LABEL_KINDS[kind]
    node: list = [token, quote(text)]
    if kind != "local":
        node.append(["shape", shape])
    node.append(["at", _num(x), _num(y), _num(angle)])
    node.append(["effects", ["font", ["size", "1.27", "1.27"]]])
    node.append(["uuid", quote(label_uuid)])
    _insert_before_trailer(tree, node)
    return label_uuid


def _num(value: float) -> str:
    """Format a coordinate/angle without trailing '.0' noise KiCad wouldn't write."""
    if float(value) == int(value):
        return str(int(value))
    return f"{float(value):g}"


def resolve_symbols_dir(kicad_cli_path: str | None) -> str | None:
    """Derive KiCad's bundled symbol-library directory from a kicad-cli.exe path.

    Standard layout: <install_root>/bin/kicad-cli.exe -> <install_root>/share/kicad/symbols/
    """
    if not kicad_cli_path:
        return None
    bin_dir = Path(kicad_cli_path).resolve().parent
    candidate = bin_dir.parent / "share" / "kicad" / "symbols"
    return str(candidate) if candidate.is_dir() else None


def load_library_symbol(symbols_dir: str, lib_id: str) -> list:
    """Load and return a library symbol's S-expression definition, renamed to its full lib_id.

    `lib_id` is "LibraryName:EntryName" (e.g. "Device:R"). Raises FileNotFoundError
    if the library file doesn't exist, ValueError if the entry isn't in it.
    The returned node's head is renamed from the bare entry name (as stored in
    the .kicad_sym file) to the full "LibraryName:EntryName" -- the convention
    real KiCad-written schematics use for symbols embedded in a schematic's
    own lib_symbols section (verified against KiCad 10.0's own demo files).
    Sub-unit symbol names (e.g. "R_0_1") are left unchanged; KiCad keeps
    those short even for the qualified top-level name.
    """
    if ":" not in lib_id:
        raise ValueError(f"lib_id must be 'Library:Entry', got {lib_id!r}")
    lib_name, entry_name = lib_id.split(":", 1)
    lib_path = os.path.join(symbols_dir, f"{lib_name}.kicad_sym")
    if not os.path.isfile(lib_path):
        raise FileNotFoundError(f"Symbol library not found: {lib_path}")

    with open(lib_path, encoding="utf-8") as f:
        lib_tree = parse(f.read())

    for sym in find_children(lib_tree, "symbol"):
        if len(sym) >= 2 and unquote(sym[1]) == entry_name:
            renamed = list(sym)
            renamed[1] = quote(lib_id)
            return renamed

    raise ValueError(f"Symbol {entry_name!r} not found in {lib_path}")


def add_component(
    tree: list,
    sch_path: str,
    lib_id: str,
    x: float,
    y: float,
    symbols_dir: str,
    angle: float = 0.0,
    reference: str = "?",
    value: str = "",
    footprint: str = "",
) -> tuple[str, str]:
    """Place a library symbol instance. Returns (symbol_uuid, assigned_reference).

    Embeds the symbol's real definition (copied from KiCad's own bundled
    library files, not hand-authored) into the schematic's lib_symbols
    section if not already present, then adds a schematic-level symbol
    instance referencing it, with one (pin "N" (uuid ...)) entry per pin the
    library definition declares and a matching (instances (project ...)) block.
    """
    existing = find_child(tree, "lib_symbols")
    lib_symbols: list = existing if existing is not None else ["lib_symbols"]
    if existing is None:
        # lib_symbols must come after paper/title_block, before content --
        # insert right after the last of (version/generator/generator_version/uuid/paper/title_block).
        header_heads = {"version", "generator", "generator_version", "uuid", "paper", "title_block"}
        insert_at = 1
        for i, child in enumerate(tree):
            if isinstance(child, list) and child and isinstance(child[0], str) and unquote(child[0]) in header_heads:
                insert_at = i + 1
        tree.insert(insert_at, lib_symbols)

    already_present = any(len(s) >= 2 and unquote(s[1]) == lib_id for s in find_children(lib_symbols, "symbol"))
    if not already_present:
        lib_def = load_library_symbol(symbols_dir, lib_id)
        lib_symbols.append(lib_def)
    else:
        lib_def = next(s for s in find_children(lib_symbols, "symbol") if unquote(s[1]) == lib_id)

    pin_numbers = _extract_pin_numbers(lib_def)

    sym_uuid = new_uuid()
    node: list = [
        "symbol",
        ["lib_id", quote(lib_id)],
        ["at", _num(x), _num(y), _num(angle)],
        ["unit", "1"],
        ["exclude_from_sim", "no"],
        ["in_bom", "yes"],
        ["on_board", "yes"],
        ["dnp", "no"],
        ["uuid", quote(sym_uuid)],
        [
            "property",
            quote("Reference"),
            quote(reference),
            ["at", _num(x), _num(y - 2.54), "0"],
            ["effects", ["font", ["size", "1.27", "1.27"]]],
        ],
        [
            "property",
            quote("Value"),
            quote(value),
            ["at", _num(x), _num(y + 2.54), "0"],
            ["effects", ["font", ["size", "1.27", "1.27"]]],
        ],
        [
            "property",
            quote("Footprint"),
            quote(footprint),
            ["at", _num(x), _num(y), "0"],
            ["effects", ["font", ["size", "1.27", "1.27"]], ["hide", "yes"]],
        ],
    ]
    for pin_num in pin_numbers:
        node.append(["pin", quote(pin_num), ["uuid", quote(new_uuid())]])

    project = project_name_for(sch_path)
    node.append(
        [
            "instances",
            [
                "project",
                quote(project),
                ["path", quote(f"/{root_uuid(tree)}"), ["reference", quote(reference)], ["unit", "1"]],
            ],
        ]
    )

    _insert_before_trailer(tree, node)
    return sym_uuid, reference


def _extract_pin_numbers(lib_symbol: list) -> list[str]:
    """Collect every pin number declared across a library symbol's unit sub-symbols."""
    numbers: list[str] = []
    for sub in find_children(lib_symbol, "symbol"):
        for pin in find_children(sub, "pin"):
            number_node = find_child(pin, "number")
            if number_node and len(number_node) >= 2:
                numbers.append(unquote(number_node[1]))
    return numbers


def annotate(tree: list) -> list[tuple[str, str]]:
    """Assign sequential reference designators to un-annotated symbols.

    A symbol is considered un-annotated if its Reference property ends in
    '?' (KiCad's own placeholder convention, e.g. "R?", "U?") or is empty.
    Existing fully-assigned references are scanned first so new assignments
    never collide with them. Returns a list of (old_reference, new_reference)
    for every symbol that was changed; updates both the symbol's Reference
    property and its instances/project/path/reference in place.
    """
    used_numbers: dict[str, set[int]] = {}
    to_annotate: list[list] = []

    symbols = find_children(tree, "symbol")
    for sym in symbols:
        ref_prop = _find_property(sym, "Reference")
        if ref_prop is None:
            continue
        ref_value = unquote(ref_prop[2])
        prefix, number = _split_reference(ref_value)
        if number is not None:
            used_numbers.setdefault(prefix, set()).add(number)
        else:
            to_annotate.append(sym)

    changes: list[tuple[str, str]] = []
    for sym in to_annotate:
        ref_prop = _find_property(sym, "Reference")
        if ref_prop is None:
            continue  # unreachable: to_annotate only contains symbols with a Reference property
        old_value = unquote(ref_prop[2])
        prefix = _KNOWN_PREFIXES.get(old_value.rstrip("?"), old_value.rstrip("?") or "U")
        n = 1
        seen = used_numbers.setdefault(prefix, set())
        while n in seen:
            n += 1
        seen.add(n)
        new_value = f"{prefix}{n}"

        ref_prop[2] = quote(new_value)
        instances = find_child(sym, "instances")
        if instances:
            for project in find_children(instances, "project"):
                for path in find_children(project, "path"):
                    path_ref = find_child(path, "reference")
                    if path_ref:
                        path_ref[1] = quote(new_value)
        changes.append((old_value, new_value))

    return changes


def _find_property(symbol_node: list, key: str) -> list | None:
    for child in symbol_node:
        if (
            isinstance(child, list)
            and len(child) >= 2
            and isinstance(child[0], str)
            and unquote(child[0]) == "property"
            and unquote(child[1]) == key
        ):
            return child
    return None


def _split_reference(ref: str) -> tuple[str, int | None]:
    """('R4', 4) for a fully-assigned reference; ('R', None) for 'R?' or 'R'."""
    i = len(ref)
    while i > 0 and ref[i - 1].isdigit():
        i -= 1
    prefix, digits = ref[:i], ref[i:]
    if digits and digits.isdigit():
        return prefix, int(digits)
    return ref.rstrip("?"), None
