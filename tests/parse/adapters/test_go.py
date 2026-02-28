from __future__ import annotations

from pathlib import Path

import pytest

from archex.models import DiscoveredFile, ImportStatement, Symbol, SymbolKind, Visibility
from archex.parse.adapters.base import LanguageAdapter
from archex.parse.adapters.go import GoAdapter
from archex.parse.engine import TreeSitterEngine

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "go_simple"


@pytest.fixture()
def engine() -> TreeSitterEngine:
    return TreeSitterEngine()


@pytest.fixture()
def adapter() -> GoAdapter:
    return GoAdapter()


def parse(engine: TreeSitterEngine, source: bytes) -> object:
    return engine.parse_bytes(source, "go")


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_satisfies_language_adapter_protocol(adapter: GoAdapter) -> None:
    assert isinstance(adapter, LanguageAdapter)


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------


def test_language_id(adapter: GoAdapter) -> None:
    assert adapter.language_id == "go"


def test_file_extensions(adapter: GoAdapter) -> None:
    assert adapter.file_extensions == [".go"]


def test_tree_sitter_name(adapter: GoAdapter) -> None:
    assert adapter.tree_sitter_name == "go"


# ---------------------------------------------------------------------------
# extract_symbols: functions
# ---------------------------------------------------------------------------


def test_extract_functions(engine: TreeSitterEngine, adapter: GoAdapter) -> None:
    source = (FIXTURES_DIR / "main.go").read_bytes()
    tree = parse(engine, source)
    symbols = adapter.extract_symbols(tree, source, "main.go")
    funcs = {s.name for s in symbols if s.kind == SymbolKind.FUNCTION}
    assert "main" in funcs
    assert "LoadConfig" in funcs


def test_function_visibility(engine: TreeSitterEngine, adapter: GoAdapter) -> None:
    source = (FIXTURES_DIR / "utils.go").read_bytes()
    tree = parse(engine, source)
    symbols = adapter.extract_symbols(tree, source, "utils.go")
    format_name = next(s for s in symbols if s.name == "FormatName")
    assert format_name.visibility == Visibility.PUBLIC
    validate = next(s for s in symbols if s.name == "validateInput")
    assert validate.visibility == Visibility.PRIVATE


def test_function_signature(engine: TreeSitterEngine, adapter: GoAdapter) -> None:
    source = (FIXTURES_DIR / "utils.go").read_bytes()
    tree = parse(engine, source)
    symbols = adapter.extract_symbols(tree, source, "utils.go")
    fn = next(s for s in symbols if s.name == "FormatName")
    assert fn.signature is not None
    assert "FormatName" in fn.signature
    assert "string" in fn.signature


# ---------------------------------------------------------------------------
# extract_symbols: types (struct, interface, alias)
# ---------------------------------------------------------------------------


def test_extract_struct_types(engine: TreeSitterEngine, adapter: GoAdapter) -> None:
    source = (FIXTURES_DIR / "models.go").read_bytes()
    tree = parse(engine, source)
    symbols = adapter.extract_symbols(tree, source, "models.go")
    types = [s for s in symbols if s.kind == SymbolKind.TYPE]
    names = {s.name for s in types}
    assert "Config" in names
    assert "User" in names
    assert "unexportedModel" in names
    assert "ID" in names  # type alias


def test_struct_visibility(engine: TreeSitterEngine, adapter: GoAdapter) -> None:
    source = (FIXTURES_DIR / "models.go").read_bytes()
    tree = parse(engine, source)
    symbols = adapter.extract_symbols(tree, source, "models.go")
    user = next(s for s in symbols if s.name == "User")
    assert user.visibility == Visibility.PUBLIC
    unexported = next(s for s in symbols if s.name == "unexportedModel")
    assert unexported.visibility == Visibility.PRIVATE


def test_extract_interfaces(engine: TreeSitterEngine, adapter: GoAdapter) -> None:
    source = (FIXTURES_DIR / "handlers.go").read_bytes()
    tree = parse(engine, source)
    symbols = adapter.extract_symbols(tree, source, "handlers.go")
    interfaces = [s for s in symbols if s.kind == SymbolKind.INTERFACE]
    names = {s.name for s in interfaces}
    assert "Handler" in names
    assert "Middleware" in names


# ---------------------------------------------------------------------------
# extract_symbols: methods
# ---------------------------------------------------------------------------


def test_extract_methods_pointer_receiver(engine: TreeSitterEngine, adapter: GoAdapter) -> None:
    source = (FIXTURES_DIR / "models.go").read_bytes()
    tree = parse(engine, source)
    symbols = adapter.extract_symbols(tree, source, "models.go")
    methods = [s for s in symbols if s.kind == SymbolKind.METHOD]
    validate = next(s for s in methods if s.name == "Validate")
    assert validate.parent == "Config"
    assert validate.qualified_name == "Config.Validate"


def test_extract_methods_value_receiver(engine: TreeSitterEngine, adapter: GoAdapter) -> None:
    source = (FIXTURES_DIR / "models.go").read_bytes()
    tree = parse(engine, source)
    symbols = adapter.extract_symbols(tree, source, "models.go")
    methods = [s for s in symbols if s.kind == SymbolKind.METHOD]
    to_json = next(s for s in methods if s.name == "ToJSON")
    assert to_json.parent == "User"
    assert to_json.qualified_name == "User.ToJSON"


def test_method_signature(engine: TreeSitterEngine, adapter: GoAdapter) -> None:
    source = (FIXTURES_DIR / "handlers.go").read_bytes()
    tree = parse(engine, source)
    symbols = adapter.extract_symbols(tree, source, "handlers.go")
    add_route = next(s for s in symbols if s.name == "AddRoute")
    assert add_route.signature is not None
    assert "r *router" in add_route.signature
    assert "AddRoute" in add_route.signature


def test_unexported_method(engine: TreeSitterEngine, adapter: GoAdapter) -> None:
    source = (FIXTURES_DIR / "handlers.go").read_bytes()
    tree = parse(engine, source)
    symbols = adapter.extract_symbols(tree, source, "handlers.go")
    handle = next(s for s in symbols if s.name == "handle")
    assert handle.visibility == Visibility.PRIVATE
    assert handle.parent == "router"


# ---------------------------------------------------------------------------
# extract_symbols: const and var
# ---------------------------------------------------------------------------


def test_extract_constants(engine: TreeSitterEngine, adapter: GoAdapter) -> None:
    source = (FIXTURES_DIR / "models.go").read_bytes()
    tree = parse(engine, source)
    symbols = adapter.extract_symbols(tree, source, "models.go")
    consts = [s for s in symbols if s.kind == SymbolKind.CONSTANT]
    names = {s.name for s in consts}
    assert "MaxRetries" in names
    assert "StatusOK" in names
    assert "statusNotFound" in names


def test_constant_visibility(engine: TreeSitterEngine, adapter: GoAdapter) -> None:
    source = (FIXTURES_DIR / "models.go").read_bytes()
    tree = parse(engine, source)
    symbols = adapter.extract_symbols(tree, source, "models.go")
    consts = {s.name: s for s in symbols if s.kind == SymbolKind.CONSTANT}
    assert consts["MaxRetries"].visibility == Visibility.PUBLIC
    assert consts["StatusOK"].visibility == Visibility.PUBLIC
    assert consts["statusNotFound"].visibility == Visibility.PRIVATE


def test_extract_variables(engine: TreeSitterEngine, adapter: GoAdapter) -> None:
    source = (FIXTURES_DIR / "models.go").read_bytes()
    tree = parse(engine, source)
    symbols = adapter.extract_symbols(tree, source, "models.go")
    variables = [s for s in symbols if s.kind == SymbolKind.VARIABLE]
    names = {s.name for s in variables}
    assert "DefaultTimeout" in names


# ---------------------------------------------------------------------------
# parse_imports: single and grouped imports
# ---------------------------------------------------------------------------


def test_parse_grouped_imports(engine: TreeSitterEngine, adapter: GoAdapter) -> None:
    source = (FIXTURES_DIR / "main.go").read_bytes()
    tree = parse(engine, source)
    imports = adapter.parse_imports(tree, source, "main.go")
    modules = {i.module for i in imports}
    assert "fmt" in modules
    assert "os" in modules


def test_parse_single_import(engine: TreeSitterEngine, adapter: GoAdapter) -> None:
    source = (FIXTURES_DIR / "models.go").read_bytes()
    tree = parse(engine, source)
    imports = adapter.parse_imports(tree, source, "models.go")
    modules = {i.module for i in imports}
    assert "encoding/json" in modules


def test_parse_blank_import(engine: TreeSitterEngine, adapter: GoAdapter) -> None:
    source = (FIXTURES_DIR / "handlers.go").read_bytes()
    tree = parse(engine, source)
    imports = adapter.parse_imports(tree, source, "handlers.go")
    embed_imp = next((i for i in imports if i.module == "embed"), None)
    assert embed_imp is not None
    assert embed_imp.alias is None  # blank import _ has no alias


def test_parse_aliased_import(engine: TreeSitterEngine, adapter: GoAdapter) -> None:
    source = b'package main\n\nimport log "github.com/sirupsen/logrus"\n'
    tree = parse(engine, source)
    imports = adapter.parse_imports(tree, source, "main.go")
    assert len(imports) == 1
    assert imports[0].module == "github.com/sirupsen/logrus"
    assert imports[0].alias == "log"


def test_imports_not_relative(engine: TreeSitterEngine, adapter: GoAdapter) -> None:
    source = (FIXTURES_DIR / "utils.go").read_bytes()
    tree = parse(engine, source)
    imports = adapter.parse_imports(tree, source, "utils.go")
    for imp in imports:
        assert imp.is_relative is False


# ---------------------------------------------------------------------------
# resolve_import
# ---------------------------------------------------------------------------


def test_resolve_internal_import(adapter: GoAdapter) -> None:
    file_map = {
        "pkg/models/user.go": "/repo/pkg/models/user.go",
    }
    imp = ImportStatement(
        module="myapp/pkg/models",
        file_path="cmd/main.go",
        line=3,
        is_relative=False,
    )
    resolved = adapter.resolve_import(imp, file_map)
    assert resolved == "/repo/pkg/models/user.go"


def test_resolve_external_returns_none(adapter: GoAdapter) -> None:
    file_map = {"main.go": "/repo/main.go"}
    imp = ImportStatement(
        module="fmt",
        file_path="main.go",
        line=3,
        is_relative=False,
    )
    resolved = adapter.resolve_import(imp, file_map)
    assert resolved is None


# ---------------------------------------------------------------------------
# classify_visibility
# ---------------------------------------------------------------------------


def test_classify_exported_symbol(adapter: GoAdapter) -> None:
    s = Symbol(
        name="Handler",
        qualified_name="Handler",
        kind=SymbolKind.INTERFACE,
        file_path="handler.go",
        start_line=1,
        end_line=5,
    )
    assert adapter.classify_visibility(s) == Visibility.PUBLIC


def test_classify_unexported_symbol(adapter: GoAdapter) -> None:
    s = Symbol(
        name="helper",
        qualified_name="helper",
        kind=SymbolKind.FUNCTION,
        file_path="utils.go",
        start_line=1,
        end_line=3,
    )
    assert adapter.classify_visibility(s) == Visibility.PRIVATE


# ---------------------------------------------------------------------------
# detect_entry_points
# ---------------------------------------------------------------------------


def test_detect_entry_point(adapter: GoAdapter) -> None:
    files = [
        DiscoveredFile(
            path="main.go",
            absolute_path=str(FIXTURES_DIR / "main.go"),
            language="go",
        ),
        DiscoveredFile(
            path="utils.go",
            absolute_path=str(FIXTURES_DIR / "utils.go"),
            language="go",
        ),
    ]
    entry_points = adapter.detect_entry_points(files)
    assert "main.go" in entry_points
    assert "utils.go" not in entry_points


def test_non_main_package_not_entry_point(adapter: GoAdapter, tmp_path: Path) -> None:
    f = tmp_path / "lib.go"
    f.write_text("package lib\n\nfunc Helper() {}\n")
    files = [DiscoveredFile(path="lib.go", absolute_path=str(f), language="go")]
    assert adapter.detect_entry_points(files) == []


# ---------------------------------------------------------------------------
# Inline source: edge cases
# ---------------------------------------------------------------------------


def test_dot_import(engine: TreeSitterEngine, adapter: GoAdapter) -> None:
    source = b'package main\n\nimport . "math"\n'
    tree = parse(engine, source)
    imports = adapter.parse_imports(tree, source, "main.go")
    assert len(imports) == 1
    assert imports[0].module == "math"
    assert imports[0].alias is None  # dot import treated like blank


def test_empty_file(engine: TreeSitterEngine, adapter: GoAdapter) -> None:
    source = b"package main\n"
    tree = parse(engine, source)
    symbols = adapter.extract_symbols(tree, source, "empty.go")
    imports = adapter.parse_imports(tree, source, "empty.go")
    assert symbols == []
    assert imports == []
