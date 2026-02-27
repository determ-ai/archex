from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from archex.acquire.local import open_local
from archex.exceptions import AcquireError

if TYPE_CHECKING:
    from pathlib import Path


def test_valid_repo(python_simple_repo: Path) -> None:
    result = open_local(python_simple_repo)
    assert result == python_simple_repo.resolve()
    assert result.is_dir()


def test_nonexistent_path(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist"
    with pytest.raises(AcquireError, match="does not exist"):
        open_local(missing)


def test_not_a_directory(tmp_path: Path) -> None:
    file = tmp_path / "not_a_dir.txt"
    file.write_text("hello")
    with pytest.raises(AcquireError, match="not a directory"):
        open_local(file)


def test_no_git_directory(tmp_path: Path) -> None:
    with pytest.raises(AcquireError, match="No .git directory"):
        open_local(tmp_path)
