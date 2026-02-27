from __future__ import annotations

from click.testing import CliRunner

from archex.cli.main import cli


def test_version() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "archex, version 0.1.0dev0" in result.output


def test_help_contains_subcommands() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    output = result.output
    assert "analyze" in output
    assert "query" in output
    assert "compare" in output
    assert "cache" in output
