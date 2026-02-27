from __future__ import annotations

from archex.models import (
    ArchProfile,
    CodeChunk,
    EdgeKind,
    PatternCategory,
    RepoMetadata,
    Symbol,
    SymbolKind,
    Visibility,
)


def test_symbol_kind_members() -> None:
    assert SymbolKind.FUNCTION == "function"
    assert SymbolKind.CLASS == "class"
    assert SymbolKind.METHOD == "method"
    assert SymbolKind.TYPE == "type"
    assert SymbolKind.VARIABLE == "variable"


def test_visibility_members() -> None:
    assert Visibility.PUBLIC == "public"
    assert Visibility.INTERNAL == "internal"
    assert Visibility.PRIVATE == "private"


def test_edge_kind_members() -> None:
    assert EdgeKind.IMPORTS == "imports"
    assert EdgeKind.CALLS == "calls"
    assert EdgeKind.INHERITS == "inherits"
    assert EdgeKind.IMPLEMENTS == "implements"


def test_pattern_category_members() -> None:
    assert PatternCategory.STRUCTURAL == "structural"
    assert PatternCategory.BEHAVIORAL == "behavioral"
    assert PatternCategory.CREATIONAL == "creational"


def test_repo_metadata_instantiation() -> None:
    meta = RepoMetadata(
        url="https://github.com/test/repo",
        total_files=10,
        total_lines=500,
    )
    assert meta.url == "https://github.com/test/repo"
    assert meta.total_files == 10
    assert meta.total_lines == 500


def test_symbol_instantiation() -> None:
    symbol = Symbol(
        name="my_function",
        qualified_name="module.my_function",
        kind=SymbolKind.FUNCTION,
        file_path="src/module.py",
        start_line=10,
        end_line=15,
        visibility=Visibility.PUBLIC,
    )
    assert symbol.name == "my_function"
    assert symbol.kind == SymbolKind.FUNCTION
    assert symbol.visibility == Visibility.PUBLIC


def test_code_chunk_instantiation() -> None:
    chunk = CodeChunk(
        id="chunk-1",
        content="def foo(): pass",
        file_path="src/module.py",
        start_line=1,
        end_line=1,
        language="python",
    )
    assert chunk.content == "def foo(): pass"
    assert chunk.file_path == "src/module.py"
    assert chunk.start_line == 1


def test_arch_profile_minimal() -> None:
    profile = ArchProfile(repo=RepoMetadata())
    assert profile.module_map == []
    assert profile.pattern_catalog == []
    assert profile.stats.total_files == 0
