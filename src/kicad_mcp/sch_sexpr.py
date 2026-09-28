"""Minimal S-expression parser/serializer for KiCad file formats (.kicad_sch, .kicad_sym).

KiCad-specific, not a general Lisp reader: handles double-quoted strings with
backslash escapes, bare atoms (numbers, bare symbols like `yes`/`no`/`default`),
and nested lists. The serializer reproduces KiCad's own tab-indented,
one-node-per-line writer convention (verified against real files written by
KiCad 10.0 -- its bundled demo schematics and Device.kicad_sym).

S-expressions are whitespace-agnostic for parsing, so a file this module
writes is always structurally valid regardless of line-break placement, even
if this serializer's cosmetic choices don't match KiCad's own writer in every
edge case. The practical consequence: the FIRST tool call that mutates a
given .kicad_sch file reformats the whole file to this module's style (a
large, all-formatting git diff, not a content change); a later manual save
from the KiCad GUI reformats it back to KiCad's own style. This is the same
tradeoff every script-based KiCad S-expression editor makes (e.g. kicad-skip).

AST shape: an atom is a `str` (verbatim token text, quotes included for
quoted strings); a list node is a Python `list` whose first element is
typically the head token (e.g. "kicad_sch", "symbol", "at").
"""

from __future__ import annotations

import re

Atom = str
SExprNode = "Atom | list"  # documentation only; not a real type alias

_WHITESPACE = " \t\r\n"


def tokenize(text: str) -> list[str]:
    """Split raw S-expression text into a flat token stream.

    Parens are their own tokens. Quoted strings (with backslash escapes) are
    kept as single tokens including their surrounding quotes. Everything
    else is a bare atom, split on whitespace/parens.
    """
    tokens: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c in _WHITESPACE:
            i += 1
            continue
        if c in "()":
            tokens.append(c)
            i += 1
            continue
        if c == '"':
            j = i + 1
            buf = ['"']
            while j < n:
                if text[j] == "\\" and j + 1 < n:
                    buf.append(text[j])
                    buf.append(text[j + 1])
                    j += 2
                    continue
                if text[j] == '"':
                    buf.append('"')
                    j += 1
                    break
                buf.append(text[j])
                j += 1
            tokens.append("".join(buf))
            i = j
            continue
        j = i
        while j < n and text[j] not in _WHITESPACE and text[j] not in "()":
            j += 1
        tokens.append(text[i:j])
        i = j
    return tokens


def parse(text: str) -> list:
    """Parse a full .kicad_sch / .kicad_sym file into a nested-list AST.

    Returns the single top-level list node (e.g. the `(kicad_sch ...)` or
    `(symbol ...)` node). Raises ValueError on malformed input (unbalanced
    parens or trailing garbage) rather than silently returning a partial
    tree -- a partially-parsed KiCad file must never be treated as valid.
    """
    tokens = tokenize(text)
    if not tokens:
        raise ValueError("Empty S-expression input")
    pos = 0

    def parse_expr():
        nonlocal pos
        if pos >= len(tokens):
            raise ValueError("Unexpected end of input while parsing S-expression")
        tok = tokens[pos]
        if tok == "(":
            pos += 1
            lst: list = []
            while True:
                if pos >= len(tokens):
                    raise ValueError("Unbalanced parentheses: missing ')'")
                if tokens[pos] == ")":
                    pos += 1
                    return lst
                lst.append(parse_expr())
        if tok == ")":
            raise ValueError("Unexpected ')' with no matching '('")
        pos += 1
        return tok

    result = parse_expr()
    if pos != len(tokens):
        raise ValueError(f"Trailing content after top-level expression ({len(tokens) - pos} tokens unconsumed)")
    if not isinstance(result, list):
        raise ValueError(f"Top-level S-expression must be a list, got bare atom {result!r}")
    return result


def serialize(node, indent: int = 0) -> str:
    """Serialize an AST node back to KiCad-style tab-indented S-expression text.

    Leading atom children (before the first sub-list child) are kept on the
    opening line with the head token, matching every real KiCad-written file
    inspected while building this module (e.g. `(property "Reference" "R4"`
    followed by `(at ...)` and `(effects ...)` each on their own line).
    Every subsequent child gets its own line, tab-indented one level deeper.
    A node with no sub-list children at all stays entirely on one line.
    """
    if isinstance(node, str):
        return node
    if not node:
        return "()"

    has_sublist = any(isinstance(c, list) for c in node)
    if not has_sublist:
        return "(" + " ".join(serialize(c) for c in node) + ")"

    pad = "\t" * (indent + 1)
    close_pad = "\t" * indent
    lines: list[str] = []
    leading: list[str] = []
    i = 0
    while i < len(node) and not isinstance(node[i], list):
        leading.append(serialize(node[i]))
        i += 1
    lines.append("(" + " ".join(leading))
    for child in node[i:]:
        lines.append(pad + serialize(child, indent + 1))
    return "\n".join(lines) + "\n" + close_pad + ")"


def serialize_file(root: list) -> str:
    """Serialize a full top-level node to file content, with trailing newline."""
    return serialize(root) + "\n"


def unquote(atom: str) -> str:
    """Strip surrounding quotes and unescape a quoted-string atom.

    Returns bare atoms (numbers, `yes`/`no`, symbols) unchanged.
    """
    if len(atom) >= 2 and atom[0] == '"' and atom[-1] == '"':
        inner = atom[1:-1]
        return re.sub(r"\\(.)", r"\1", inner)
    return atom


def quote(value: str) -> str:
    """Quote and escape a string for use as an S-expression atom."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def find_child(node: list, head: str) -> list | None:
    """Return the first direct child list whose head atom equals `head`, or None."""
    for child in node:
        if isinstance(child, list) and child and isinstance(child[0], str) and unquote(child[0]) == head:
            return child
    return None


def find_children(node: list, head: str) -> list[list]:
    """Return all direct child lists whose head atom equals `head`."""
    return [
        child
        for child in node
        if isinstance(child, list) and child and isinstance(child[0], str) and unquote(child[0]) == head
    ]
