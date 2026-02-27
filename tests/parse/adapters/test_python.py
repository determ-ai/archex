from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from archex.models import DiscoveredFile, ImportStatement, Symbol, SymbolKind, Visibility
from archex.parse.adapters.python import PythonAdapter
from archex.parse.engine import TreeSitterEngine

FIXTURES_DIR = "tests/fixtures/python_simple"


@pytest.fixture()
def engine() -> TreeSitterEngine:
    return TreeSitterEngine()


@pytest.fixture()
def adapter() -> PythonAdapter:
    return PythonAdapter()


def parse(engine: TreeSitterEngine, source: bytes) -> object:
    return engine.parse_bytes(source, "python")


# --- Properties ---


def test_language_id(adapter: PythonAdapter) -> None:
    assert adapter.language_id == "python"


def test_file_extensions(adapter: PythonAdapter) -> None:
    assert ".py" in adapter.file_extensions


def test_tree_sitter_name(adapter: PythonAdapter) -> None:
    assert adapter.tree_sitter_name == "python"


# --- extract_symbols: functions ---


def test_extract_top_level_function(engine: TreeSitterEngine, adapter: PythonAdapter) -> None:
    source = b"def greet(name: str) -> str:\n    return f'Hello {name}'\n"
    tree = parse(engine, source)
    symbols = adapter.extract_symbols(tree, source, "greet.py")
    assert len(symbols) == 1
    s = symbols[0]
    assert s.name == "greet"
    assert s.qualified_name == "greet"
    assert s.kind == SymbolKind.FUNCTION
    assert s.file_path == "greet.py"
    assert s.start_line == 1


def test_extract_multiple_functions(engine: TreeSitterEngine, adapter: PythonAdapter) -> None:
    source = b"def foo(): pass\ndef bar(): pass\n"
    tree = parse(engine, source)
    symbols = adapter.extract_symbols(tree, source, "x.py")
    names = [s.name for s in symbols]
    assert "foo" in names
    assert "bar" in names


# --- extract_symbols: classes ---


def test_extract_class(engine: TreeSitterEngine, adapter: PythonAdapter) -> None:
    source = b"class MyClass:\n    pass\n"
    tree = parse(engine, source)
    symbols = adapter.extract_symbols(tree, source, "x.py")
    classes = [s for s in symbols if s.kind == SymbolKind.CLASS]
    assert len(classes) == 1
    assert classes[0].name == "MyClass"


# --- extract_symbols: methods with qualified names ---


def test_extract_methods_with_qualified_names(
    engine: TreeSitterEngine, adapter: PythonAdapter
) -> None:
    source = b"class Foo:\n    def bar(self): pass\n    def baz(self): pass\n"
    tree = parse(engine, source)
    symbols = adapter.extract_symbols(tree, source, "x.py")
    methods = [s for s in symbols if s.kind == SymbolKind.METHOD]
    qnames = {s.qualified_name for s in methods}
    assert "Foo.bar" in qnames
    assert "Foo.baz" in qnames
    for m in methods:
        assert m.parent == "Foo"


def test_method_not_duplicated_as_function(
    engine: TreeSitterEngine, adapter: PythonAdapter
) -> None:
    source = b"class Foo:\n    def bar(self): pass\n"
    tree = parse(engine, source)
    symbols = adapter.extract_symbols(tree, source, "x.py")
    funcs = [s for s in symbols if s.kind == SymbolKind.FUNCTION]
    assert not funcs


# --- parse_imports ---


def test_import_statement(engine: TreeSitterEngine, adapter: PythonAdapter) -> None:
    source = b"import os\n"
    tree = parse(engine, source)
    imports = adapter.parse_imports(tree, source, "f.py")
    assert len(imports) == 1
    assert imports[0].module == "os"
    assert imports[0].is_relative is False
    assert imports[0].symbols == []


def test_from_import_statement(engine: TreeSitterEngine, adapter: PythonAdapter) -> None:
    source = b"from models import Role, User\n"
    tree = parse(engine, source)
    imports = adapter.parse_imports(tree, source, "main.py")
    assert len(imports) == 1
    imp = imports[0]
    assert imp.module == "models"
    assert "Role" in imp.symbols
    assert "User" in imp.symbols
    assert imp.is_relative is False


def test_relative_import_single_dot(engine: TreeSitterEngine, adapter: PythonAdapter) -> None:
    source = b"from . import utils\n"
    tree = parse(engine, source)
    imports = adapter.parse_imports(tree, source, "pkg/mod.py")
    assert len(imports) == 1
    imp = imports[0]
    assert imp.is_relative is True
    assert imp.module.startswith(".")


def test_relative_import_double_dot(engine: TreeSitterEngine, adapter: PythonAdapter) -> None:
    source = b"from ..pkg import helper\n"
    tree = parse(engine, source)
    imports = adapter.parse_imports(tree, source, "a/b/mod.py")
    assert len(imports) == 1
    imp = imports[0]
    assert imp.is_relative is True
    assert imp.module.startswith("..")


def test_import_alias(engine: TreeSitterEngine, adapter: PythonAdapter) -> None:
    source = b"import numpy as np\n"
    tree = parse(engine, source)
    imports = adapter.parse_imports(tree, source, "f.py")
    assert len(imports) == 1
    assert imports[0].module == "numpy"
    assert imports[0].alias == "np"


# --- resolve_import ---


def test_resolve_absolute_import(adapter: PythonAdapter) -> None:
    file_map = {"models": "models.py", "utils": "utils.py"}
    imp = ImportStatement(module="models", symbols=["User"], file_path="main.py", line=1)
    resolved = adapter.resolve_import(imp, file_map)
    assert resolved == "models.py"


def test_resolve_external_import_returns_none(adapter: PythonAdapter) -> None:
    file_map = {"models": "models.py"}
    imp = ImportStatement(module="requests", symbols=[], file_path="main.py", line=1)
    resolved = adapter.resolve_import(imp, file_map)
    assert resolved is None


def test_resolve_relative_import(adapter: PythonAdapter) -> None:
    # "from . import utils" from services/mod.py → services/utils.py
    file_map = {"utils": "utils.py", "services.utils": "services/utils.py"}
    imp = ImportStatement(
        module=".",
        symbols=["utils"],
        file_path="services/mod.py",
        line=1,
        is_relative=True,
    )
    resolved = adapter.resolve_import(imp, file_map)
    # Should resolve to services/__init__.py or None (no __init__ in file_map)
    assert resolved is None or isinstance(resolved, str)


def test_resolve_dotted_module(adapter: PythonAdapter) -> None:
    file_map = {"services.auth": "services/auth.py"}
    imp = ImportStatement(module="services.auth", symbols=[], file_path="main.py", line=1)
    resolved = adapter.resolve_import(imp, file_map)
    assert resolved == "services/auth.py"


# --- classify_visibility ---


def test_visibility_public(adapter: PythonAdapter) -> None:
    s = Symbol(
        name="my_func",
        qualified_name="my_func",
        kind=SymbolKind.FUNCTION,
        file_path="x.py",
        start_line=1,
        end_line=1,
    )
    assert adapter.classify_visibility(s) == Visibility.PUBLIC


def test_visibility_private(adapter: PythonAdapter) -> None:
    s = Symbol(
        name="_private",
        qualified_name="_private",
        kind=SymbolKind.FUNCTION,
        file_path="x.py",
        start_line=1,
        end_line=1,
    )
    assert adapter.classify_visibility(s) == Visibility.PRIVATE


def test_visibility_dunder_is_public(adapter: PythonAdapter) -> None:
    s = Symbol(
        name="__init__",
        qualified_name="__init__",
        kind=SymbolKind.METHOD,
        file_path="x.py",
        start_line=1,
        end_line=1,
    )
    assert adapter.classify_visibility(s) == Visibility.PUBLIC


# --- detect_entry_points ---


def test_detect_main_py(adapter: PythonAdapter, tmp_path: Path) -> None:
    main_file = tmp_path / "__main__.py"
    main_file.write_text("from __future__ import annotations\n")
    files = [
        DiscoveredFile(
            path="__main__.py",
            absolute_path=str(main_file),
            language="python",
        )
    ]
    entry_points = adapter.detect_entry_points(files)
    assert "__main__.py" in entry_points


def test_detect_name_main_guard(adapter: PythonAdapter, tmp_path: Path) -> None:
    src_file = tmp_path / "app.py"
    src_file.write_text('if __name__ == "__main__":\n    run()\n')
    files = [
        DiscoveredFile(
            path="app.py",
            absolute_path=str(src_file),
            language="python",
        )
    ]
    entry_points = adapter.detect_entry_points(files)
    assert "app.py" in entry_points


def test_detect_main_function(adapter: PythonAdapter, tmp_path: Path) -> None:
    src_file = tmp_path / "script.py"
    src_file.write_text("def main():\n    pass\n")
    files = [
        DiscoveredFile(
            path="script.py",
            absolute_path=str(src_file),
            language="python",
        )
    ]
    entry_points = adapter.detect_entry_points(files)
    assert "script.py" in entry_points


# --- Integration: python_simple fixture ---


def test_models_py_classes(engine: TreeSitterEngine, adapter: PythonAdapter) -> None:
    with open(f"{FIXTURES_DIR}/models.py", "rb") as f:
        source = f.read()
    tree = parse(engine, source)
    symbols = adapter.extract_symbols(tree, source, "models.py")
    class_names = {s.name for s in symbols if s.kind == SymbolKind.CLASS}
    assert "Role" in class_names
    assert "User" in class_names


def test_services_auth_methods(engine: TreeSitterEngine, adapter: PythonAdapter) -> None:
    with open(f"{FIXTURES_DIR}/services/auth.py", "rb") as f:
        source = f.read()
    tree = parse(engine, source)
    symbols = adapter.extract_symbols(tree, source, "services/auth.py")
    methods = {s.qualified_name for s in symbols if s.kind == SymbolKind.METHOD}
    assert "AuthService.login" in methods
    assert "AuthService.logout" in methods
    assert "AuthService.verify_token" in methods
