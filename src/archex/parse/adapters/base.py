"""Abstract base class for language-specific parse adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from archex.models import DiscoveredFile, ImportStatement, Symbol, Visibility


@runtime_checkable
class LanguageAdapter(Protocol):
    """Protocol for language-specific parse adapters."""

    @property
    def language_id(self) -> str:
        """Unique language identifier (e.g., 'python', 'typescript')."""
        ...

    @property
    def file_extensions(self) -> list[str]:
        """List of file extensions handled by this adapter (e.g., ['.py'])."""
        ...

    @property
    def tree_sitter_name(self) -> str:
        """tree-sitter grammar name (e.g., 'python')."""
        ...

    def extract_symbols(
        self, tree: object, source: bytes, file_path: str
    ) -> list[Symbol]:
        """Extract all symbols (functions, classes, methods) from a parsed tree."""
        ...

    def parse_imports(
        self, tree: object, source: bytes, file_path: str
    ) -> list[ImportStatement]:
        """Extract all import statements from a parsed tree."""
        ...

    def resolve_import(
        self, imp: ImportStatement, file_map: dict[str, str]
    ) -> str | None:
        """Resolve an import to an absolute file path, or None if external."""
        ...

    def detect_entry_points(self, files: list[DiscoveredFile]) -> list[str]:
        """Return file paths that are entry points (e.g., __main__.py)."""
        ...

    def classify_visibility(self, symbol: Symbol) -> Visibility:
        """Classify a symbol's visibility based on naming conventions."""
        ...
