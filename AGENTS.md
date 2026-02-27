# AGENTS.md — archex

## Project

**archex** is a Python library for architecture extraction and codebase intelligence. It parses source code into structured representations (AST, call graphs, dependency graphs) suitable for RAG pipelines and agentic workflows.

## Directory Layout

```
archex/
├── src/archex/          # Library source
│   ├── cli/             # Click CLI entrypoint (archex.cli.main:cli)
│   ├── parsers/         # Tree-sitter language parsers
│   ├── graph/           # NetworkX-based dependency/call graphs
│   ├── chunking/        # Token-aware code chunkers (tiktoken)
│   └── models/          # Pydantic v2 data models
├── tests/               # pytest test suite
├── docs/                # Project documentation
├── pyproject.toml       # Project config (hatchling build)
├── .pre-commit-config.yaml
└── .github/workflows/ci.yml
```

## Key Commands

```bash
uv sync --dev         # Install all dependencies including dev
uv run pytest         # Run test suite
uv run ruff check .   # Lint
uv run ruff format .  # Format
uv run pyright .      # Type check
uv run archex --help  # CLI entrypoint
```

## Coding Conventions

- Python 3.11+ with `from __future__ import annotations`
- Pydantic v2 for all data models
- ruff for linting and formatting (line-length = 100)
- pyright in strict mode — no `Any`, full type coverage
- tree-sitter >= 0.23 API for parsing
- networkx for graph operations
- No fallbacks, no silent failures — fail fast and loud
- DRY, single source of truth, no placeholder variables
