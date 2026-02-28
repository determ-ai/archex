from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from archex import __version__
from archex.cli.main import cli

if TYPE_CHECKING:
    from pathlib import Path


def test_version() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert f"archex, version {__version__}" in result.output


def test_help_contains_subcommands() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    output = result.output
    assert "analyze" in output
    assert "query" in output
    assert "compare" in output
    assert "cache" in output


def test_analyze_local_json(python_simple_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["analyze", str(python_simple_repo), "--format", "json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert "repo" in data
    assert "stats" in data
    assert "interface_surface" in data


def test_analyze_local_markdown(python_simple_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["analyze", str(python_simple_repo), "--format", "markdown"])
    assert result.exit_code == 0, result.output
    output = result.output
    assert "# Architecture Profile" in output
    assert "## Stats" in output


def test_analyze_error_handling() -> None:
    from unittest.mock import patch

    from archex.exceptions import ArchexError

    runner = CliRunner()
    with patch("archex.cli.analyze_cmd.analyze", side_effect=ArchexError("Test error")):
        result = runner.invoke(cli, ["analyze", "/fake/repo"])
    assert result.exit_code != 0
    assert "Test error" in result.output


def test_query_error_handling(python_simple_repo: Path) -> None:
    from unittest.mock import patch

    from archex.exceptions import ArchexError

    runner = CliRunner()
    with patch("archex.cli.query_cmd.query", side_effect=ArchexError("Query failed")):
        result = runner.invoke(cli, ["query", str(python_simple_repo), "test question"])
    assert result.exit_code != 0
    assert "Query failed" in result.output


def test_compare_error_handling() -> None:
    from unittest.mock import patch

    from archex.exceptions import ArchexError

    runner = CliRunner()
    with patch("archex.cli.compare_cmd.compare", side_effect=ArchexError("Analyze failed")):
        result = runner.invoke(cli, ["compare", "/fake/a", "/fake/b"])
    assert result.exit_code != 0
    assert "Analyze failed" in result.output


def test_compare_type_check_raises_type_error() -> None:
    from archex.cli.compare_cmd import render_comparison_markdown

    # Test that non-ComparisonResult raises TypeError
    with pytest.raises(TypeError, match="Expected ComparisonResult"):
        render_comparison_markdown({"not": "a_comparison_result"})


class TestCacheList:
    def test_empty_cache(self, tmp_path: Path) -> None:
        runner = CliRunner()
        cache_dir = str(tmp_path / "empty_cache")
        result = runner.invoke(cli, ["cache", "list", "--cache-dir", cache_dir])
        assert result.exit_code == 0
        assert "No cached entries" in result.output

    def test_lists_entries(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        # Create a fake cache entry
        key = "a" * 64
        (cache_dir / f"{key}.db").write_text("fake")
        (cache_dir / f"{key}.meta").write_text("1234567890.0")

        runner = CliRunner()
        result = runner.invoke(cli, ["cache", "list", "--cache-dir", str(cache_dir)])
        assert result.exit_code == 0
        assert key[:12] in result.output


class TestCacheClean:
    def test_clean_removes_old(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        key = "b" * 64
        (cache_dir / f"{key}.db").write_text("fake")
        (cache_dir / f"{key}.meta").write_text("0")  # epoch = very old

        runner = CliRunner()
        result = runner.invoke(
            cli, ["cache", "clean", "--max-age", "1", "--cache-dir", str(cache_dir)]
        )
        assert result.exit_code == 0
        assert "Removed 1" in result.output

    def test_clean_keeps_recent(self, tmp_path: Path) -> None:
        import time

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        key = "c" * 64
        (cache_dir / f"{key}.db").write_text("fake")
        (cache_dir / f"{key}.meta").write_text(str(time.time()))

        runner = CliRunner()
        result = runner.invoke(
            cli, ["cache", "clean", "--max-age", "24", "--cache-dir", str(cache_dir)]
        )
        assert result.exit_code == 0
        assert "Removed 0" in result.output


class TestCacheInfo:
    def test_info_output(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        runner = CliRunner()
        result = runner.invoke(cli, ["cache", "info", "--cache-dir", str(cache_dir)])
        assert result.exit_code == 0
        assert "Cache directory" in result.output
        assert "Total entries" in result.output
        assert "Total size" in result.output
