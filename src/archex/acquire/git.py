"""Git-based repository acquisition: clone, sparse-checkout, and commit pinning."""

from __future__ import annotations

import subprocess
from pathlib import Path

from archex.exceptions import AcquireError


def clone_repo(
    url: str,
    target_dir: str | Path,
    shallow: bool = True,
    branch: str | None = None,
) -> Path:
    """Clone a git repository to target_dir and return the resolved path.

    Raises AcquireError on subprocess failure or timeout.
    """
    target = Path(target_dir).resolve()
    cmd: list[str] = ["git", "clone"]

    if shallow:
        cmd += ["--depth", "1"]

    if branch is not None:
        cmd += ["--branch", branch]

    cmd += [url, str(target)]

    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode(errors="replace").strip()
        raise AcquireError(f"git clone failed for {url!r}: {stderr}") from exc
    except subprocess.TimeoutExpired as exc:
        raise AcquireError(f"git clone timed out after 120s for {url!r}") from exc

    return target
