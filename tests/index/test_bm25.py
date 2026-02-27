"""Tests for BM25Index: keyword search over CodeChunks using SQLite FTS5."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

from archex.index.bm25 import BM25Index
from archex.index.store import IndexStore
from archex.models import CodeChunk, SymbolKind

SAMPLE_CHUNKS = [
    CodeChunk(
        id="utils.py:calculate_sum:5",
        content="def calculate_sum(a: int, b: int) -> int:\n    return a + b",
        file_path="utils.py",
        start_line=5,
        end_line=6,
        symbol_name="calculate_sum",
        symbol_kind=SymbolKind.FUNCTION,
        language="python",
        token_count=20,
    ),
    CodeChunk(
        id="auth.py:authenticate:10",
        content=(
            "def authenticate(username: str, password: str) -> bool:\n"
            "    return check_credentials(username, password)"
        ),
        file_path="auth.py",
        start_line=10,
        end_line=11,
        symbol_name="authenticate",
        symbol_kind=SymbolKind.FUNCTION,
        language="python",
        token_count=25,
    ),
    CodeChunk(
        id="models.py:User:1",
        content=(
            "class User:\n"
            "    def __init__(self, name: str, email: str) -> None:\n"
            "        self.name = name\n"
            "        self.email = email"
        ),
        file_path="models.py",
        start_line=1,
        end_line=4,
        symbol_name="User",
        symbol_kind=SymbolKind.CLASS,
        language="python",
        token_count=35,
    ),
]


@pytest.fixture
def store_and_index(tmp_path: Path) -> Generator[tuple[IndexStore, BM25Index], None, None]:
    db = tmp_path / "bm25_test.db"
    s = IndexStore(db)
    idx = BM25Index(s)
    s.insert_chunks(SAMPLE_CHUNKS)
    idx.build(SAMPLE_CHUNKS)
    yield s, idx
    s.close()


def test_build_and_search_returns_results(store_and_index: tuple[IndexStore, BM25Index]) -> None:
    _, idx = store_and_index
    results = idx.search("calculate")
    assert len(results) > 0


def test_search_function_name_returns_correct_chunk(
    store_and_index: tuple[IndexStore, BM25Index],
) -> None:
    _, idx = store_and_index
    results = idx.search("authenticate")
    assert len(results) > 0
    top_chunk, _ = results[0]
    assert top_chunk.id == "auth.py:authenticate:10"


def test_search_class_name_returns_user_chunk(
    store_and_index: tuple[IndexStore, BM25Index],
) -> None:
    _, idx = store_and_index
    results = idx.search("User")
    assert len(results) > 0
    ids = [c.id for c, _ in results]
    assert "models.py:User:1" in ids


def test_search_keyword_in_content(store_and_index: tuple[IndexStore, BM25Index]) -> None:
    _, idx = store_and_index
    results = idx.search("password")
    assert len(results) > 0
    top_chunk, _ = results[0]
    assert top_chunk.id == "auth.py:authenticate:10"


def test_results_sorted_by_relevance(store_and_index: tuple[IndexStore, BM25Index]) -> None:
    _, idx = store_and_index
    results = idx.search("str")
    assert len(results) > 0
    scores = [score for _, score in results]
    assert scores == sorted(scores, reverse=True)


def test_top_k_limits_results(store_and_index: tuple[IndexStore, BM25Index]) -> None:
    _, idx = store_and_index
    results = idx.search("str", top_k=1)
    assert len(results) <= 1


def test_empty_query_returns_empty_list(store_and_index: tuple[IndexStore, BM25Index]) -> None:
    _, idx = store_and_index
    assert idx.search("") == []
    assert idx.search("   ") == []


def test_no_matches_returns_empty_list(store_and_index: tuple[IndexStore, BM25Index]) -> None:
    _, idx = store_and_index
    results = idx.search("xyzzy_nonexistent_token_12345")
    assert results == []


def test_scores_are_positive(store_and_index: tuple[IndexStore, BM25Index]) -> None:
    _, idx = store_and_index
    results = idx.search("def")
    for _, score in results:
        assert score > 0


def test_build_is_idempotent(store_and_index: tuple[IndexStore, BM25Index]) -> None:
    _, idx = store_and_index
    # Rebuilding should not duplicate results
    idx.build(SAMPLE_CHUNKS)
    results = idx.search("authenticate")
    # Should only return one result for authenticate, not two
    auth_chunks = [c for c, _ in results if c.id == "auth.py:authenticate:10"]
    assert len(auth_chunks) == 1
