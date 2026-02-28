"""Tests for VectorIndex and reciprocal_rank_fusion."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import pytest

from archex.exceptions import ArchexIndexError
from archex.index.vector import VectorIndex, reciprocal_rank_fusion
from archex.models import CodeChunk, SymbolKind

if TYPE_CHECKING:
    from pathlib import Path


class FakeEmbedder:
    """Deterministic test embedder using content hashes for reproducible vectors."""

    def __init__(self, dim: int = 64) -> None:
        self._dim = dim

    def encode(self, texts: list[str]) -> list[list[float]]:
        results: list[list[float]] = []
        for text in texts:
            h = hashlib.sha256(text.encode()).digest()
            raw: list[float] = []
            for i in range(self._dim):
                byte_val = h[i % len(h)]
                raw.append((byte_val / 255.0) * 2 - 1)
            results.append(raw)
        return results

    @property
    def dimension(self) -> int:
        return self._dim


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
    CodeChunk(
        id="math.py:add:1",
        content="def add(x: int, y: int) -> int:\n    return x + y",
        file_path="math.py",
        start_line=1,
        end_line=2,
        symbol_name="add",
        symbol_kind=SymbolKind.FUNCTION,
        language="python",
        token_count=18,
    ),
]


@pytest.fixture
def embedder() -> FakeEmbedder:
    return FakeEmbedder(dim=64)


@pytest.fixture
def built_index(embedder: FakeEmbedder) -> VectorIndex:
    idx = VectorIndex()
    idx.build(SAMPLE_CHUNKS, embedder)
    return idx


class TestVectorIndexBuild:
    def test_build_sets_size(self, built_index: VectorIndex) -> None:
        assert built_index.size == 4

    def test_build_empty_chunks(self, embedder: FakeEmbedder) -> None:
        idx = VectorIndex()
        idx.build([], embedder)
        assert idx.size == 0

    def test_build_single_chunk(self, embedder: FakeEmbedder) -> None:
        idx = VectorIndex()
        idx.build([SAMPLE_CHUNKS[0]], embedder)
        assert idx.size == 1


class TestVectorIndexSearch:
    def test_search_returns_results(self, built_index: VectorIndex, embedder: FakeEmbedder) -> None:
        results = built_index.search("calculate sum", embedder)
        assert len(results) > 0

    def test_search_returns_tuples_of_chunk_and_score(
        self, built_index: VectorIndex, embedder: FakeEmbedder
    ) -> None:
        results = built_index.search("function", embedder)
        for chunk, score in results:
            assert isinstance(chunk, CodeChunk)
            assert isinstance(score, float)

    def test_search_scores_are_positive(
        self, built_index: VectorIndex, embedder: FakeEmbedder
    ) -> None:
        results = built_index.search("user model", embedder)
        for _, score in results:
            assert score > 0

    def test_search_top_k_limits_results(
        self, built_index: VectorIndex, embedder: FakeEmbedder
    ) -> None:
        results = built_index.search("def", embedder, top_k=2)
        assert len(results) <= 2

    def test_search_empty_index(self, embedder: FakeEmbedder) -> None:
        idx = VectorIndex()
        results = idx.search("test", embedder)
        assert results == []

    def test_search_results_sorted_by_score(
        self, built_index: VectorIndex, embedder: FakeEmbedder
    ) -> None:
        results = built_index.search("function def", embedder)
        scores = [s for _, s in results]
        assert scores == sorted(scores, reverse=True)

    def test_search_similar_content_ranks_higher(
        self, built_index: VectorIndex, embedder: FakeEmbedder
    ) -> None:
        # Query with exact content should return that chunk first
        results = built_index.search(
            "def calculate_sum(a: int, b: int) -> int:\n    return a + b",
            embedder,
        )
        assert len(results) > 0
        assert results[0][0].id == "utils.py:calculate_sum:5"


class TestVectorIndexPersistence:
    def test_save_and_load_roundtrip(
        self, built_index: VectorIndex, embedder: FakeEmbedder, tmp_path: Path
    ) -> None:
        save_path = tmp_path / "vectors.npz"
        built_index.save(save_path)

        loaded = VectorIndex()
        loaded.load(save_path, SAMPLE_CHUNKS)
        assert loaded.size == built_index.size

        # Search results should match
        original = built_index.search("user", embedder)
        restored = loaded.search("user", embedder)
        assert len(original) == len(restored)
        for (oc, os_), (rc, rs) in zip(original, restored, strict=True):
            assert oc.id == rc.id
            assert abs(os_ - rs) < 1e-5

    def test_save_empty_index_raises(self, tmp_path: Path) -> None:
        idx = VectorIndex()
        with pytest.raises(ArchexIndexError, match="empty"):
            idx.save(tmp_path / "empty.npz")

    def test_load_missing_file_raises(self, tmp_path: Path) -> None:
        idx = VectorIndex()
        with pytest.raises(ArchexIndexError, match="not found"):
            idx.load(tmp_path / "nonexistent.npz", [])

    def test_save_creates_parent_dirs(self, built_index: VectorIndex, tmp_path: Path) -> None:
        save_path = tmp_path / "sub" / "dir" / "vectors.npz"
        built_index.save(save_path)
        assert save_path.exists()


class TestReciprocalRankFusion:
    def test_rrf_merges_results(self) -> None:
        bm25: list[tuple[CodeChunk, float]] = [
            (SAMPLE_CHUNKS[0], 5.0),
            (SAMPLE_CHUNKS[1], 3.0),
        ]
        vector: list[tuple[CodeChunk, float]] = [
            (SAMPLE_CHUNKS[1], 0.9),
            (SAMPLE_CHUNKS[2], 0.8),
        ]
        merged = reciprocal_rank_fusion(bm25, vector)
        ids = [c.id for c, _ in merged]
        # chunk[1] appears in both lists, should rank highest
        assert ids[0] == SAMPLE_CHUNKS[1].id
        assert len(merged) == 3

    def test_rrf_deduplicates(self) -> None:
        bm25: list[tuple[CodeChunk, float]] = [
            (SAMPLE_CHUNKS[0], 5.0),
        ]
        vector: list[tuple[CodeChunk, float]] = [
            (SAMPLE_CHUNKS[0], 0.9),
        ]
        merged = reciprocal_rank_fusion(bm25, vector)
        assert len(merged) == 1

    def test_rrf_empty_inputs(self) -> None:
        assert reciprocal_rank_fusion([], []) == []

    def test_rrf_one_empty_list(self) -> None:
        bm25: list[tuple[CodeChunk, float]] = [
            (SAMPLE_CHUNKS[0], 5.0),
            (SAMPLE_CHUNKS[1], 3.0),
        ]
        merged = reciprocal_rank_fusion(bm25, [])
        assert len(merged) == 2

    def test_rrf_scores_are_positive(self) -> None:
        bm25: list[tuple[CodeChunk, float]] = [(SAMPLE_CHUNKS[0], 1.0)]
        vector: list[tuple[CodeChunk, float]] = [(SAMPLE_CHUNKS[1], 0.5)]
        merged = reciprocal_rank_fusion(bm25, vector)
        for _, score in merged:
            assert score > 0

    def test_rrf_custom_k(self) -> None:
        bm25: list[tuple[CodeChunk, float]] = [(SAMPLE_CHUNKS[0], 1.0)]
        vector: list[tuple[CodeChunk, float]] = [(SAMPLE_CHUNKS[0], 0.5)]
        result_k10 = reciprocal_rank_fusion(bm25, vector, k=10)
        result_k100 = reciprocal_rank_fusion(bm25, vector, k=100)
        # Higher k → lower individual scores
        assert result_k10[0][1] > result_k100[0][1]

    def test_rrf_preserves_all_chunks(self) -> None:
        bm25: list[tuple[CodeChunk, float]] = [
            (SAMPLE_CHUNKS[0], 5.0),
            (SAMPLE_CHUNKS[1], 3.0),
        ]
        vector: list[tuple[CodeChunk, float]] = [
            (SAMPLE_CHUNKS[2], 0.9),
            (SAMPLE_CHUNKS[3], 0.8),
        ]
        merged = reciprocal_rank_fusion(bm25, vector)
        assert len(merged) == 4
