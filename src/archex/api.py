"""Top-level public API: analyze, query, and compare entry points."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from archex.models import (
        ArchProfile,
        ComparisonResult,
        Config,
        ContextBundle,
        IndexConfig,
        RepoSource,
    )


def analyze(
    source: RepoSource,
    config: Config | None = None,
    index_config: IndexConfig | None = None,
) -> ArchProfile:
    """Acquire, parse, index, and analyze a repository."""
    # TODO: Implement in Phase 2
    raise NotImplementedError


def query(
    profile: ArchProfile,
    query: str,
    token_budget: int = 8192,
) -> ContextBundle:
    """Retrieve a ranked ContextBundle for a natural-language query."""
    # TODO: Implement in Phase 3
    raise NotImplementedError


def compare(
    source_a: RepoSource,
    source_b: RepoSource,
    config: Config | None = None,
) -> ComparisonResult:
    """Analyze two repositories and return a ComparisonResult."""
    # TODO: Implement in Phase 4
    raise NotImplementedError
