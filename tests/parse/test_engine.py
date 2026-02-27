from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from archex.exceptions import ParseError
from archex.parse.engine import TreeSitterEngine

PYTHON_SOURCE = b"def hello():\n    pass\n"


def _root(tree: object) -> Any:
    t: Any = tree
    return t.root_node


def test_parse_python_source() -> None:
    engine = TreeSitterEngine()
    tree = engine.parse_bytes(PYTHON_SOURCE, "python")
    root = _root(tree)
    assert root is not None
    assert root.type == "module"


def test_parse_bytes_returns_tree_with_children() -> None:
    engine = TreeSitterEngine()
    source = b"class Foo:\n    def bar(self):\n        pass\n"
    tree = engine.parse_bytes(source, "python")
    root = _root(tree)
    assert len(root.children) > 0


def test_parser_caching_returns_same_instance() -> None:
    engine = TreeSitterEngine()
    parser1 = engine.get_parser("python")
    parser2 = engine.get_parser("python")
    assert parser1 is parser2


def test_language_caching_returns_same_instance() -> None:
    engine = TreeSitterEngine()
    lang1 = engine.get_language("python")
    lang2 = engine.get_language("python")
    assert lang1 is lang2


def test_unsupported_language_raises_parse_error() -> None:
    engine = TreeSitterEngine()
    with pytest.raises(ParseError, match="Unsupported language"):
        engine.get_language("cobol")


def test_parse_file(tmp_path: Path) -> None:
    source_file = tmp_path / "sample.py"
    source_file.write_bytes(PYTHON_SOURCE)
    engine = TreeSitterEngine()
    tree = engine.parse_file(str(source_file), "python")
    root = _root(tree)
    assert root.type == "module"


def test_parse_file_missing_raises_parse_error(tmp_path: Path) -> None:
    engine = TreeSitterEngine()
    with pytest.raises(ParseError, match="Failed to read file"):
        engine.parse_file(str(tmp_path / "nonexistent.py"), "python")
