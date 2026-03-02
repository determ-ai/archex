"""Token efficiency reporting for MCP tool responses."""

from __future__ import annotations

import tiktoken

from archex.models import TokenMeta

_encoder = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Count tokens using the cl100k_base encoding."""
    return len(_encoder.encode(text))


def compute_meta(
    *,
    tool_name: str,
    response_text: str,
    raw_file_tokens: int,
    strategy: str,
    cached: bool = False,
    index_time_ms: float = 0.0,
    query_time_ms: float = 0.0,
) -> TokenMeta:
    """Compute token efficiency metrics for a tool response."""
    returned = count_tokens(response_text)
    savings = (1 - returned / raw_file_tokens) * 100 if raw_file_tokens > 0 else 0.0
    return TokenMeta(
        tokens_returned=returned,
        tokens_raw_equivalent=raw_file_tokens,
        savings_pct=round(savings, 1),
        strategy=strategy,
        tool_name=tool_name,
        cached=cached,
        index_time_ms=round(index_time_ms, 1),
        query_time_ms=round(query_time_ms, 1),
    )
