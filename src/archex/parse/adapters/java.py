"""Java parse adapter: extract symbols and imports from .java files using tree-sitter."""

from __future__ import annotations

from typing import Any

from archex.models import DiscoveredFile, ImportStatement, Symbol, SymbolKind, Visibility
from archex.parse.adapters._jvm_helpers import map_jvm_visibility, resolve_jvm_import
from archex.parse.adapters.ts_node import (
    ts_children as _children,
)
from archex.parse.adapters.ts_node import (
    ts_end_line as _end_line,
)
from archex.parse.adapters.ts_node import (
    ts_field as _field,
)
from archex.parse.adapters.ts_node import (
    ts_named_children as _named_children,
)
from archex.parse.adapters.ts_node import (
    ts_start_line as _start_line,
)
from archex.parse.adapters.ts_node import (
    ts_text as _text,
)
from archex.parse.adapters.ts_node import (
    ts_type as _type,
)

# ---------------------------------------------------------------------------
# Modifier helpers
# ---------------------------------------------------------------------------


def _extract_visibility(node: object, default: Visibility = Visibility.INTERNAL) -> Visibility:
    """Extract visibility from a node's modifiers child.

    *default* is returned when no access modifier is present.  Java class members
    default to package-private (INTERNAL); interface members default to PUBLIC.
    """
    for child in _children(node):
        if _type(child) != "modifiers":
            continue
        for mod in _children(child):
            mod_type = _type(mod)
            if mod_type in ("public", "private", "protected"):
                return map_jvm_visibility(mod_type)
    return default


def _has_modifier(node: object, source: bytes, modifier: str) -> bool:
    """Check if a node has a specific modifier keyword."""
    for child in _children(node):
        if _type(child) != "modifiers":
            continue
        for mod in _children(child):
            if _text(mod, source) == modifier:
                return True
    return False


def _is_static_final(node: object, source: bytes) -> bool:
    """Check if a field has both static and final modifiers (→ CONSTANT)."""
    return _has_modifier(node, source, "static") and _has_modifier(node, source, "final")


# ---------------------------------------------------------------------------
# Signature helpers
# ---------------------------------------------------------------------------


def _build_method_signature(node: object, source: bytes, name: str, return_type: str) -> str:
    """Build a method signature string."""
    params_node = _field(node, "parameters")
    params = _text(params_node, source) if params_node else "()"
    return f"{return_type} {name}{params}"


def _get_return_type(node: object, source: bytes) -> str:
    """Extract the return type from a method or constructor."""
    type_node = _field(node, "type")
    if type_node:
        return _text(type_node, source)
    # Check for void_type child
    for child in _children(node):
        ct = _type(child)
        if ct == "void_type":
            return "void"
        if ct in (
            "type_identifier",
            "generic_type",
            "integral_type",
            "boolean_type",
            "floating_point_type",
            "array_type",
        ):
            return _text(child, source)
    return "void"


# ---------------------------------------------------------------------------
# Symbol extraction
# ---------------------------------------------------------------------------


def _extract_class_symbols(
    node: object, source: bytes, file_path: str, parent_name: str | None = None
) -> list[Symbol]:
    """Extract a class declaration and its members."""
    name_node = _field(node, "name")
    if name_node is None:
        return []
    name = _text(name_node, source)
    qualified = f"{parent_name}.{name}" if parent_name else name
    vis = _extract_visibility(node)

    symbols: list[Symbol] = [
        Symbol(
            name=name,
            qualified_name=qualified,
            kind=SymbolKind.CLASS,
            file_path=file_path,
            start_line=_start_line(node),
            end_line=_end_line(node),
            visibility=vis,
            parent=parent_name,
        )
    ]

    body = _field(node, "body")
    if body is not None:
        symbols.extend(_extract_body_members(body, source, file_path, qualified))

    return symbols


def _extract_interface_symbols(
    node: object, source: bytes, file_path: str, parent_name: str | None = None
) -> list[Symbol]:
    """Extract an interface declaration and its method declarations."""
    name_node = _field(node, "name")
    if name_node is None:
        return []
    name = _text(name_node, source)
    qualified = f"{parent_name}.{name}" if parent_name else name
    vis = _extract_visibility(node)

    symbols: list[Symbol] = [
        Symbol(
            name=name,
            qualified_name=qualified,
            kind=SymbolKind.INTERFACE,
            file_path=file_path,
            start_line=_start_line(node),
            end_line=_end_line(node),
            visibility=vis,
            parent=parent_name,
        )
    ]

    body = _field(node, "body")
    if body is not None:
        symbols.extend(
            _extract_body_members(
                body,
                source,
                file_path,
                qualified,
                default_visibility=Visibility.PUBLIC,
            )
        )

    return symbols


def _extract_enum_symbols(
    node: object, source: bytes, file_path: str, parent_name: str | None = None
) -> list[Symbol]:
    """Extract an enum declaration and its members."""
    name_node = _field(node, "name")
    if name_node is None:
        return []
    name = _text(name_node, source)
    qualified = f"{parent_name}.{name}" if parent_name else name
    vis = _extract_visibility(node)

    symbols: list[Symbol] = [
        Symbol(
            name=name,
            qualified_name=qualified,
            kind=SymbolKind.ENUM,
            file_path=file_path,
            start_line=_start_line(node),
            end_line=_end_line(node),
            visibility=vis,
            parent=parent_name,
        )
    ]

    body = _field(node, "body")
    if body is not None:
        for child in _named_children(body):
            ct = _type(child)
            if ct == "enum_constant":
                cname_node = _field(child, "name")
                if cname_node:
                    cname = _text(cname_node, source)
                    symbols.append(
                        Symbol(
                            name=cname,
                            qualified_name=f"{qualified}.{cname}",
                            kind=SymbolKind.CONSTANT,
                            file_path=file_path,
                            start_line=_start_line(child),
                            end_line=_end_line(child),
                            visibility=vis,
                            parent=qualified,
                        )
                    )
            elif ct == "enum_body_declarations":
                symbols.extend(_extract_body_members(child, source, file_path, qualified))

    return symbols


def _extract_method(
    node: object,
    source: bytes,
    file_path: str,
    parent_name: str,
    default_visibility: Visibility = Visibility.INTERNAL,
) -> Symbol | None:
    """Extract a method declaration."""
    name_node = _field(node, "name")
    if name_node is None:
        return None
    name = _text(name_node, source)
    vis = _extract_visibility(node, default=default_visibility)
    ret_type = _get_return_type(node, source)
    sig = _build_method_signature(node, source, name, ret_type)

    return Symbol(
        name=name,
        qualified_name=f"{parent_name}.{name}",
        kind=SymbolKind.METHOD,
        file_path=file_path,
        start_line=_start_line(node),
        end_line=_end_line(node),
        visibility=vis,
        signature=sig,
        parent=parent_name,
    )


def _extract_constructor(
    node: object,
    source: bytes,
    file_path: str,
    parent_name: str,
    default_visibility: Visibility = Visibility.INTERNAL,
) -> Symbol | None:
    """Extract a constructor declaration (treated as METHOD)."""
    name_node = _field(node, "name")
    if name_node is None:
        return None
    name = _text(name_node, source)
    vis = _extract_visibility(node, default=default_visibility)
    params_node = _field(node, "parameters")
    params = _text(params_node, source) if params_node else "()"
    sig = f"{name}{params}"

    return Symbol(
        name=name,
        qualified_name=f"{parent_name}.{name}",
        kind=SymbolKind.METHOD,
        file_path=file_path,
        start_line=_start_line(node),
        end_line=_end_line(node),
        visibility=vis,
        signature=sig,
        parent=parent_name,
    )


def _extract_field(node: object, source: bytes, file_path: str, parent_name: str) -> list[Symbol]:
    """Extract field declarations (may declare multiple variables)."""
    symbols: list[Symbol] = []
    vis = _extract_visibility(node)
    is_constant = _is_static_final(node, source)
    kind = SymbolKind.CONSTANT if is_constant else SymbolKind.VARIABLE

    for child in _named_children(node):
        if _type(child) != "variable_declarator":
            continue
        name_node = _field(child, "name")
        if name_node is None:
            continue
        name = _text(name_node, source)
        symbols.append(
            Symbol(
                name=name,
                qualified_name=f"{parent_name}.{name}",
                kind=kind,
                file_path=file_path,
                start_line=_start_line(node),
                end_line=_end_line(node),
                visibility=vis,
                parent=parent_name,
            )
        )

    return symbols


def _extract_body_members(
    body: object,
    source: bytes,
    file_path: str,
    parent_name: str,
    *,
    default_visibility: Visibility = Visibility.INTERNAL,
) -> list[Symbol]:
    """Extract all member symbols from a class/interface/enum body."""
    symbols: list[Symbol] = []

    for child in _named_children(body):
        ct = _type(child)

        if ct == "method_declaration":
            sym = _extract_method(child, source, file_path, parent_name, default_visibility)
            if sym:
                symbols.append(sym)
        elif ct == "constructor_declaration":
            sym = _extract_constructor(child, source, file_path, parent_name, default_visibility)
            if sym:
                symbols.append(sym)
        elif ct == "field_declaration":
            symbols.extend(_extract_field(child, source, file_path, parent_name))
        elif ct in ("class_declaration", "record_declaration"):
            symbols.extend(_extract_class_symbols(child, source, file_path, parent_name))
        elif ct == "interface_declaration":
            symbols.extend(_extract_interface_symbols(child, source, file_path, parent_name))
        elif ct == "enum_declaration":
            symbols.extend(_extract_enum_symbols(child, source, file_path, parent_name))
        elif ct == "annotation_type_declaration":
            name_node = _field(child, "name")
            if name_node:
                name = _text(name_node, source)
                vis = _extract_visibility(child)
                symbols.append(
                    Symbol(
                        name=name,
                        qualified_name=f"{parent_name}.{name}",
                        kind=SymbolKind.TYPE,
                        file_path=file_path,
                        start_line=_start_line(child),
                        end_line=_end_line(child),
                        visibility=vis,
                        parent=parent_name,
                    )
                )

    return symbols


# ---------------------------------------------------------------------------
# Import parsing
# ---------------------------------------------------------------------------


def _parse_java_import(node: object, source: bytes, file_path: str) -> ImportStatement | None:
    """Parse a single import_declaration node."""
    line = _start_line(node)
    is_static = False
    module_parts: list[str] = []

    for child in _children(node):
        ct = _type(child)
        if ct == "static":
            is_static = True
        elif ct == "scoped_identifier":
            module_parts = [_text(child, source)]
        elif ct == "asterisk" and module_parts:
            module_parts[0] += ".*"

    if not module_parts:
        return None

    module = module_parts[0]
    symbols: list[str] = []

    if is_static:
        # static import: last segment is the member name
        parts = module.rsplit(".", 1)
        if len(parts) == 2:
            module = parts[0]
            symbols = [parts[1]]

    return ImportStatement(
        module=module,
        symbols=symbols,
        file_path=file_path,
        line=line,
        is_relative=False,
    )


# ---------------------------------------------------------------------------
# JavaAdapter
# ---------------------------------------------------------------------------


class JavaAdapter:
    """Language adapter for Java source files."""

    @property
    def language_id(self) -> str:
        return "java"

    @property
    def file_extensions(self) -> list[str]:
        return [".java"]

    @property
    def tree_sitter_name(self) -> str:
        return "java"

    def extract_symbols(self, tree: object, source: bytes, file_path: str) -> list[Symbol]:
        """Extract all symbols from a Java parse tree."""
        t: Any = tree
        root: object = t.root_node
        symbols: list[Symbol] = []

        for child in _named_children(root):
            ct = _type(child)
            if ct in ("class_declaration", "record_declaration"):
                symbols.extend(_extract_class_symbols(child, source, file_path))
            elif ct == "interface_declaration":
                symbols.extend(_extract_interface_symbols(child, source, file_path))
            elif ct == "enum_declaration":
                symbols.extend(_extract_enum_symbols(child, source, file_path))

        return symbols

    def parse_imports(self, tree: object, source: bytes, file_path: str) -> list[ImportStatement]:
        """Extract all import declarations from a Java parse tree."""
        t: Any = tree
        root: object = t.root_node
        imports: list[ImportStatement] = []

        for child in _named_children(root):
            if _type(child) == "import_declaration":
                imp = _parse_java_import(child, source, file_path)
                if imp:
                    imports.append(imp)

        return imports

    def resolve_import(self, imp: ImportStatement, file_map: dict[str, str]) -> str | None:
        """Resolve a Java import to a local file, or None if external."""
        return resolve_jvm_import(imp.module, file_map, extensions=(".java",))

    def detect_entry_points(self, files: list[DiscoveredFile]) -> list[str]:
        """Detect Java entry points: main methods and framework annotations."""
        entry_points: list[str] = []
        entry_markers = (
            "public static void main(String",
            "@SpringBootApplication",
            "@Test",
        )

        for f in files:
            try:
                with open(f.absolute_path, encoding="utf-8", errors="replace") as fh:
                    content = fh.read()
            except OSError:
                continue

            if any(marker in content for marker in entry_markers):
                entry_points.append(f.path)

        return entry_points

    def classify_visibility(self, symbol: Symbol) -> Visibility:
        """Return the symbol's stored visibility (set during extraction)."""
        return symbol.visibility
