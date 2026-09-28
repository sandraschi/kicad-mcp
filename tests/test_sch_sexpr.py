"""Tests for the minimal KiCad S-expression parser/serializer."""

from __future__ import annotations

import pytest

from kicad_mcp.sch_sexpr import (
    find_child,
    find_children,
    parse,
    quote,
    serialize,
    serialize_file,
    tokenize,
    unquote,
)


def test_tokenize_simple():
    assert tokenize("(a b c)") == ["(", "a", "b", "c", ")"]


def test_tokenize_quoted_string_with_spaces():
    assert tokenize('(property "Reference" "R1")') == ["(", "property", '"Reference"', '"R1"', ")"]


def test_tokenize_quoted_string_with_escaped_quote():
    tokens = tokenize(r'(text "a \"quoted\" word")')
    assert tokens[2] == r'"a \"quoted\" word"'


def test_parse_nested():
    tree = parse("(kicad_sch (version 20250114) (paper A4))")
    assert tree[0] == "kicad_sch"
    assert tree[1] == ["version", "20250114"]
    assert tree[2] == ["paper", "A4"]


def test_parse_unbalanced_raises():
    with pytest.raises(ValueError, match="Unbalanced"):
        parse("(kicad_sch (version 1)")


def test_parse_trailing_content_raises():
    with pytest.raises(ValueError, match="Trailing"):
        parse("(a) (b)")


def test_parse_empty_raises():
    with pytest.raises(ValueError, match="Empty"):
        parse("")


def test_parse_bare_atom_top_level_raises():
    with pytest.raises(ValueError, match="must be a list"):
        parse("bare_atom")


def test_serialize_flat_list_stays_one_line():
    assert serialize(["at", "1", "2", "0"]) == "(at 1 2 0)"


def test_serialize_nested_list_multiline():
    node = ["property", '"Reference"', '"R1"', ["at", "1", "2", "0"]]
    out = serialize(node)
    assert out == '(property "Reference" "R1"\n\t(at 1 2 0)\n)'


def test_roundtrip_preserves_structure():
    original = '(kicad_sch\n\t(version 20250114)\n\t(uuid "abc")\n\t(paper "A4")\n)'
    tree = parse(original)
    out = serialize_file(tree)
    tree2 = parse(out)
    assert tree == tree2


def test_quote_unquote_roundtrip():
    assert unquote(quote("hello world")) == "hello world"
    assert unquote(quote('has "quotes" inside')) == 'has "quotes" inside'


def test_unquote_bare_atom_passthrough():
    assert unquote("20250114") == "20250114"
    assert unquote("yes") == "yes"


def test_find_child_and_find_children():
    tree = parse('(symbol (pin "1") (pin "2") (uuid "x"))')
    assert find_child(tree, "uuid") == ["uuid", '"x"']
    pins = find_children(tree, "pin")
    assert len(pins) == 2
    assert unquote(pins[0][1]) == "1"
    assert unquote(pins[1][1]) == "2"


def test_find_child_missing_returns_none():
    tree = parse("(symbol (uuid 1))")
    assert find_child(tree, "nonexistent") is None
