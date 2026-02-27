from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from archex.acquire.git import clone_repo
from archex.exceptions import AcquireError

if TYPE_CHECKING:
    from pathlib import Path


def test_clone_success(tmp_path: Path) -> None:
    target = tmp_path / "cloned"
    with patch("archex.acquire.git.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = clone_repo("https://example.com/repo.git", target)
    assert result == target.resolve()
    args = mock_run.call_args[0][0]
    assert "git" in args
    assert "clone" in args
    assert str(target.resolve()) in args


def test_clone_shallow_flag(tmp_path: Path) -> None:
    target = tmp_path / "shallow"
    with patch("archex.acquire.git.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        clone_repo("https://example.com/repo.git", target, shallow=True)
    args = mock_run.call_args[0][0]
    assert "--depth" in args
    assert "1" in args


def test_clone_no_shallow_flag(tmp_path: Path) -> None:
    target = tmp_path / "full"
    with patch("archex.acquire.git.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        clone_repo("https://example.com/repo.git", target, shallow=False)
    args = mock_run.call_args[0][0]
    assert "--depth" not in args


def test_invalid_url_raises(tmp_path: Path) -> None:
    target = tmp_path / "bad"
    with patch("archex.acquire.git.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(
            128, "git clone", stderr=b"repository not found"
        )
        with pytest.raises(AcquireError, match="git clone failed"):
            clone_repo("https://invalid.example/no-repo.git", target)


def test_timeout_raises(tmp_path: Path) -> None:
    target = tmp_path / "timeout"
    with patch("archex.acquire.git.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired("git clone", 120)
        with pytest.raises(AcquireError, match="timed out"):
            clone_repo("https://example.com/slow.git", target)


@pytest.mark.network
def test_clone_real_repo(tmp_path: Path) -> None:
    target = tmp_path / "real"
    result = clone_repo(
        "https://github.com/pallets/click.git",
        target,
        shallow=True,
    )
    assert result.exists()
    assert (result / ".git").exists()
