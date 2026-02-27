"""Local filesystem repository acquisition: path validation and normalization."""

from __future__ import annotations

from pathlib import Path

from archex.exceptions import AcquireError


def open_local(path: str | Path) -> Path:
    """Validate and return the absolute path to a local git repository.

    Raises AcquireError if the path does not exist, is not a directory,
    or does not contain a .git directory.
    """
    repo_path = Path(path).resolve()

    if not repo_path.exists():
        raise AcquireError(f"Path does not exist: {repo_path}")

    if not repo_path.is_dir():
        raise AcquireError(f"Path is not a directory: {repo_path}")

    if not (repo_path / ".git").exists():
        raise AcquireError(f"No .git directory found at: {repo_path}")

    return repo_path
