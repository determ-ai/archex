from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixture_path():
    def _fixture_path(name: str) -> Path:
        path = FIXTURES_DIR / name
        if not path.exists():
            raise FileNotFoundError(f"Fixture '{name}' not found at {path}")
        return path

    return _fixture_path


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def python_simple_repo(tmp_path: Path) -> Path:
    """Copy tests/fixtures/python_simple to a temp dir and initialise a git repo."""
    src = FIXTURES_DIR / "python_simple"
    dest = tmp_path / "python_simple"
    shutil.copytree(src, dest)

    subprocess.run(["git", "init"], cwd=dest, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@archex.test"],
        cwd=dest,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "archex-test"],
        cwd=dest,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "add", "."], cwd=dest, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=dest,
        check=True,
        capture_output=True,
    )

    return dest
