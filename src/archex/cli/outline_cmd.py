"""CLI outline subcommand: display the symbol hierarchy for a single file."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import click

from archex.api import file_outline
from archex.exceptions import ArchexError
from archex.utils import resolve_source

if TYPE_CHECKING:
    from archex.models import SymbolOutline


def _render_symbols(symbols: list[SymbolOutline], indent: int = 0) -> list[str]:
    lines: list[str] = []
    pad = "  " * indent
    for sym in symbols:
        sig = f" {sym.signature}" if sym.signature else ""
        lines.append(f"{pad}{sym.kind} {sym.name} [L{sym.start_line}-{sym.end_line}]{sig}")
        lines.extend(_render_symbols(sym.children, indent + 1))
    return lines


@click.command("outline")
@click.argument("source")
@click.argument("file_path")
@click.option("--json", "output_json", is_flag=True, default=False, help="Output as JSON.")
@click.option("--timing", is_flag=True, default=False, help="Print timing breakdown.")
def outline_cmd(source: str, file_path: str, output_json: bool, timing: bool) -> None:
    """Display the symbol outline for a single file in a repository."""
    source_obj = resolve_source(source)

    t0 = time.perf_counter()
    try:
        result = file_outline(source_obj, file_path=file_path)
    except ArchexError as exc:
        raise click.ClickException(str(exc)) from exc
    elapsed_ms = (time.perf_counter() - t0) * 1000

    if output_json:
        click.echo(result.model_dump_json(indent=2))
    else:
        click.echo(f"file: {result.file_path}")
        click.echo(f"language: {result.language}")
        click.echo(f"lines: {result.lines}")
        for line in _render_symbols(result.symbols):
            click.echo(line)

    if timing:
        click.echo(f"\n--- Timing: {elapsed_ms:.0f}ms total ---", err=True)
