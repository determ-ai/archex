"""CLI tree subcommand: display annotated file tree for a repository."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import click

from archex.api import file_tree
from archex.exceptions import ArchexError
from archex.utils import resolve_source

if TYPE_CHECKING:
    from archex.models import FileTreeEntry


def _render_tree(
    entries: list[FileTreeEntry], prefix: str = "", is_last_list: list[bool] | None = None
) -> list[str]:
    lines: list[str] = []
    for i, entry in enumerate(entries):
        is_last = i == len(entries) - 1
        connector = "+-- " if is_last else "|-- "
        if entry.is_directory:
            name = entry.path.split("/")[-1] + "/"
            lines.append(f"{prefix}{connector}{name}")
            child_prefix = prefix + ("    " if is_last else "|   ")
            lines.extend(_render_tree(entry.children, child_prefix))
        else:
            name = entry.path.split("/")[-1]
            lang = entry.language or "unknown"
            info = f"{lang}, {entry.lines} lines, {entry.symbol_count} symbols"
            lines.append(f"{prefix}{connector}{name} ({info})")
    return lines


@click.command("tree")
@click.argument("source")
@click.option("--depth", default=5, type=int, help="Maximum directory depth.")
@click.option("-l", "--language", default=None, help="Filter to specific language.")
@click.option("--json", "output_json", is_flag=True, default=False, help="Output as JSON.")
@click.option("--timing", is_flag=True, default=False, help="Print timing breakdown.")
def tree_cmd(
    source: str, depth: int, language: str | None, output_json: bool, timing: bool
) -> None:
    """Display the annotated file tree of a repository."""
    source_obj = resolve_source(source)

    t0 = time.perf_counter()
    try:
        result = file_tree(source_obj, max_depth=depth, language=language)
    except ArchexError as exc:
        raise click.ClickException(str(exc)) from exc
    elapsed_ms = (time.perf_counter() - t0) * 1000

    if output_json:
        click.echo(result.model_dump_json(indent=2))
    else:
        click.echo(result.root)
        for line in _render_tree(result.entries):
            click.echo(line)

    if timing:
        click.echo(f"\n--- Timing: {elapsed_ms:.0f}ms total ---", err=True)
