# archex

Architecture extraction and codebase intelligence for the agentic era.

archex is a Python library and CLI that transforms any Git repository into structured architectural intelligence and token-budget-aware code context. It serves two consumers from a single index: **human architects** receive an `ArchProfile` with module boundaries, dependency graphs, detected patterns, and interface surfaces; **AI agents** receive a `ContextBundle` with relevance-ranked, syntax-aligned code chunks assembled to fit within a specified token budget.

## Features

- **4 language adapters** — Python, TypeScript/JavaScript, Go, Rust (tree-sitter AST parsing)
- **3 public APIs** — `analyze()`, `query()`, `compare()`
- **Hybrid retrieval** — BM25 keyword search + optional vector embeddings with reciprocal rank fusion
- **Token budget assembly** — AST-aware chunking, dependency-graph expansion, greedy bin-packing
- **Structural analysis** — module detection (Louvain), pattern recognition, interface extraction
- **Cross-repo comparison** — 6 architectural dimensions, no LLM required
- **LLM-optional** — entire structural pipeline runs without API calls; LLM enrichment is opt-in

## Installation

```bash
pip install archex
```

### Extras

| Extra                  | What it adds                             |
| ---------------------- | ---------------------------------------- |
| `archex[vector]`       | ONNX-based local embeddings (Nomic Code) |
| `archex[vector-torch]` | Torch-backed sentence-transformers       |
| `archex[voyage]`       | Voyage Code API embeddings               |
| `archex[openai]`       | OpenAI API embeddings + LLM enrichment   |
| `archex[anthropic]`    | Anthropic API LLM enrichment             |
| `archex[all]`          | All optional dependencies                |

## Quick Start

### Python API

```python
from archex import analyze, query, compare
from archex.models import RepoSource

# Architectural analysis
profile = analyze(RepoSource(local_path="./my-project"))
for module in profile.module_map:
    print(f"{module.name}: {len(module.files)} files")
for pattern in profile.pattern_catalog:
    print(f"[{pattern.confidence:.0%}] {pattern.name}")

# Implementation context for an agent
bundle = query(
    RepoSource(local_path="./my-project"),
    "How does authentication work?",
    token_budget=8192,
)
print(bundle.to_prompt(format="xml"))

# Cross-repo comparison
result = compare(
    RepoSource(local_path="./project-a"),
    RepoSource(local_path="./project-b"),
    dimensions=["error_handling", "api_surface"],
)
```

### CLI

```bash
# Analyze a local repo or remote URL
archex analyze ./my-project --format json
archex analyze https://github.com/org/repo --format markdown -l python --timing

# Query for implementation context
archex query ./my-project "How does auth work?" --budget 8192 --format xml
archex query ./my-project "connection pooling" --strategy hybrid --timing

# Compare two repositories
archex compare ./project-a ./project-b --dimensions error_handling,api_surface --format markdown

# Manage the analysis cache
archex cache list
archex cache clean --max-age 168
archex cache info
```

## CLI Reference

### `archex analyze <source>`

Analyze a repository and produce an architecture profile.

| Option              | Default | Description                       |
| ------------------- | ------- | --------------------------------- |
| `--format`          | `json`  | Output format: `json`, `markdown` |
| `-l` / `--language` | all     | Filter by language (repeatable)   |
| `--timing`          | off     | Print timing breakdown to stderr  |

### `archex query <source> <question>`

Query a repository and return a context bundle.

| Option              | Default | Description                              |
| ------------------- | ------- | ---------------------------------------- |
| `--budget`          | `8192`  | Token budget for context assembly        |
| `--format`          | `xml`   | Output format: `xml`, `json`, `markdown` |
| `-l` / `--language` | all     | Filter by language (repeatable)          |
| `--strategy`        | `bm25`  | Retrieval strategy: `bm25`, `hybrid`     |
| `--timing`          | off     | Print timing breakdown to stderr         |

### `archex compare <source_a> <source_b>`

Compare two repositories across architectural dimensions.

| Option              | Default | Description                       |
| ------------------- | ------- | --------------------------------- |
| `--dimensions`      | all 6   | Comma-separated dimension list    |
| `--format`          | `json`  | Output format: `json`, `markdown` |
| `-l` / `--language` | all     | Filter by language (repeatable)   |

Supported dimensions: `api_surface`, `concurrency`, `configuration`, `error_handling`, `state_management`, `testing`.

### `archex cache <subcommand>`

Manage the local analysis cache.

| Subcommand | Options                              | Description            |
| ---------- | ------------------------------------ | ---------------------- |
| `list`     | `--cache-dir`                        | List cached entries    |
| `clean`    | `--max-age N` (hours), `--cache-dir` | Remove expired entries |
| `info`     | `--cache-dir`                        | Show cache summary     |

## Development

```bash
git clone https://github.com/AetherForge/archex.git
cd archex
uv sync --all-extras

# Run tests (372 tests)
uv run pytest

# Lint and format
uv run ruff check .
uv run ruff format .

# Type check (strict mode)
uv run pyright
```

## License

Apache 2.0 — see [LICENSE](LICENSE).
