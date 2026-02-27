from __future__ import annotations

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
