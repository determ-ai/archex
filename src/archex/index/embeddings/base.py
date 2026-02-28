"""Embedder protocol: defines the interface for embedding providers."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Embedder(Protocol):
    """Protocol for embedding providers that encode text into dense vectors."""

    def encode(self, texts: list[str]) -> list[list[float]]: ...

    @property
    def dimension(self) -> int: ...
