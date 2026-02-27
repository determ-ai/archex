"""Source parsing: dispatch files to language adapters and aggregate ParsedFile results."""

from __future__ import annotations

from archex.parse.adapters.base import LanguageAdapter
from archex.parse.engine import TreeSitterEngine
from archex.parse.imports import build_file_map, parse_imports, resolve_imports
from archex.parse.symbols import extract_symbols

__all__ = [
    "TreeSitterEngine",
    "LanguageAdapter",
    "extract_symbols",
    "parse_imports",
    "resolve_imports",
    "build_file_map",
]
