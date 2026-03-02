"""Top-level public API: analyze, query, and compare entry points."""

from __future__ import annotations

import logging
import shutil
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING

from archex.acquire import clone_repo, discover_files, open_local
from archex.analyze.decisions import infer_decisions
from archex.analyze.interfaces import extract_interfaces
from archex.analyze.modules import detect_modules
from archex.analyze.patterns import detect_patterns
from archex.cache import CacheManager
from archex.index.bm25 import BM25Index
from archex.index.chunker import ASTChunker, Chunker
from archex.index.graph import DependencyGraph
from archex.index.store import IndexStore
from archex.models import (
    ArchProfile,
    CodeChunk,
    Config,
    ContextBundle,
    FileOutline,
    FileTree,
    FileTreeEntry,
    IndexConfig,
    RepoMetadata,
    RepoSource,
    ScoringWeights,
    SymbolKind,
    SymbolMatch,
    SymbolOutline,
    SymbolSource,
    Visibility,
)
from archex.parse import (
    TreeSitterEngine,
    build_file_map,
    extract_symbols,
    parse_imports,
    resolve_imports,
)
from archex.parse.adapters import LanguageAdapter, default_adapter_registry
from archex.providers.base import get_provider
from archex.serve.compare import compare_repos
from archex.serve.context import assemble_context
from archex.serve.profile import build_profile

if TYPE_CHECKING:
    from collections.abc import Callable

    from archex.models import ComparisonResult

# ---------------------------------------------------------------------------
# Shared helpers for Tier 1 precision tools
# ---------------------------------------------------------------------------


def _ensure_index(
    source: RepoSource,
    config: Config | None = None,
) -> IndexStore:
    """Ensure the repo is indexed and return an open IndexStore.

    On cache hit, returns the cached store directly.
    On cache miss, runs the full acquire → parse → chunk → store pipeline.
    The caller is responsible for closing the returned store.
    """
    if config is None:
        config = Config()

    cache = CacheManager(cache_dir=config.cache_dir)
    cache_key = cache.cache_key(source)

    cached_db = cache.get(cache_key) if config.cache else None
    if cached_db is not None:
        store = IndexStore(cached_db)
        if not store.needs_reindex():
            return store
        store.close()
        cache.invalidate(cache_key)

    repo_path, _url, _local_path, cleanup = _acquire(source)
    try:
        files = discover_files(
            repo_path, languages=config.languages, max_file_size=config.max_file_size
        )
        engine = TreeSitterEngine()
        adapters = _build_adapters()
        parsed_files = extract_symbols(files, engine, adapters, parallel=config.parallel)
        import_map = parse_imports(files, engine, adapters, parallel=config.parallel)
        file_map = build_file_map(files)
        file_languages = {f.path: f.language for f in files}
        resolved_map = resolve_imports(import_map, file_map, adapters, file_languages)

        graph = DependencyGraph.from_parsed_files(parsed_files, resolved_map)

        index_config = IndexConfig()
        file_chunker: Chunker = ASTChunker(config=index_config)
        sources: dict[str, bytes] = {}
        for f in files:
            try:
                sources[f.path] = Path(f.absolute_path).read_bytes()
            except OSError:
                continue
        all_chunks = file_chunker.chunk_files(parsed_files, sources)

        db_path = Path(tempfile.mkdtemp()) / "index.db"
        store = IndexStore(db_path)
        store.insert_chunks(all_chunks)
        edges = graph.file_edges()
        store.insert_edges(edges)

        if config.cache:
            store.conn.execute("PRAGMA wal_checkpoint(FULL)")
            cache.put(cache_key, db_path)

        return store
    finally:
        cleanup()


def _chunk_to_symbol_source(chunk: CodeChunk) -> SymbolSource:
    """Convert a CodeChunk to a SymbolSource model."""
    return SymbolSource(
        symbol_id=chunk.symbol_id or chunk.id,
        name=chunk.symbol_name or "",
        kind=chunk.symbol_kind or SymbolKind.VARIABLE,
        file_path=chunk.file_path,
        start_line=chunk.start_line,
        end_line=chunk.end_line,
        signature=chunk.signature,
        visibility=Visibility(chunk.visibility) if chunk.visibility else Visibility.PUBLIC,
        docstring=chunk.docstring,
        source=chunk.content,
        imports_context=chunk.imports_context,
        token_count=chunk.token_count,
    )


def _chunk_to_symbol_outline(chunk: CodeChunk) -> SymbolOutline:
    """Convert a CodeChunk to a SymbolOutline (no source code)."""
    return SymbolOutline(
        symbol_id=chunk.symbol_id or chunk.id,
        name=chunk.symbol_name or "",
        kind=chunk.symbol_kind or SymbolKind.VARIABLE,
        file_path=chunk.file_path,
        start_line=chunk.start_line,
        end_line=chunk.end_line,
        signature=chunk.signature,
        visibility=Visibility(chunk.visibility) if chunk.visibility else Visibility.PUBLIC,
        docstring=chunk.docstring,
    )


def _chunk_to_symbol_match(chunk: CodeChunk, score: float = 0.0) -> SymbolMatch:
    """Convert a CodeChunk to a SymbolMatch (search result)."""
    return SymbolMatch(
        symbol_id=chunk.symbol_id or chunk.id,
        name=chunk.symbol_name or "",
        kind=chunk.symbol_kind or SymbolKind.VARIABLE,
        file_path=chunk.file_path,
        start_line=chunk.start_line,
        signature=chunk.signature,
        visibility=Visibility(chunk.visibility) if chunk.visibility else Visibility.PUBLIC,
        relevance_score=score,
    )


logger = logging.getLogger(__name__)


def _elapsed_ms(start: float) -> float:
    return (time.perf_counter() - start) * 1000


def _acquire(source: RepoSource) -> tuple[Path, str | None, str | None, Callable[[], None]]:
    """Resolve a RepoSource to a local path, returning a cleanup callable."""
    if source.url and (source.url.startswith("http://") or source.url.startswith("https://")):
        target_dir = tempfile.mkdtemp()

        def _url_cleanup() -> None:
            shutil.rmtree(target_dir, ignore_errors=True)

        return clone_repo(source.url, target_dir), source.url, None, _url_cleanup

    if source.local_path is not None:

        def _noop() -> None:
            pass

        return open_local(source.local_path), None, source.local_path, _noop
    raise ValueError("RepoSource must have a url or local_path")


def _build_adapters() -> dict[str, LanguageAdapter]:
    """Build the registry of language adapters from the default registry."""
    return default_adapter_registry.build_all()


def analyze(
    source: RepoSource,
    config: Config | None = None,
) -> ArchProfile:
    """Acquire, parse, index, and analyze a repository.

    Runs the full pipeline: acquire → parse → graph → modules → patterns → interfaces
    → optional LLM enrichment → profile assembly.
    """
    if config is None:
        config = Config()

    t0 = time.perf_counter()
    repo_path, url, local_path, cleanup = _acquire(source)
    logger.info("Acquired repo %s in %.0fms", url or local_path, _elapsed_ms(t0))
    try:
        t1 = time.perf_counter()
        files = discover_files(
            repo_path, languages=config.languages, max_file_size=config.max_file_size
        )
        logger.info("Discovered %d files in %.0fms", len(files), _elapsed_ms(t1))

        engine = TreeSitterEngine()
        adapters = _build_adapters()

        t2 = time.perf_counter()
        parsed_files = extract_symbols(files, engine, adapters, parallel=config.parallel)
        import_map = parse_imports(files, engine, adapters, parallel=config.parallel)
        file_map = build_file_map(files)
        file_languages = {f.path: f.language for f in files}
        resolved_map = resolve_imports(import_map, file_map, adapters, file_languages)
        logger.info("Parsed %d files in %.0fms", len(parsed_files), _elapsed_ms(t2))

        graph = DependencyGraph.from_parsed_files(parsed_files, resolved_map)

        t3 = time.perf_counter()
        modules = detect_modules(graph, parsed_files)
        patterns = detect_patterns(parsed_files, graph)
        interfaces = extract_interfaces(parsed_files, graph)
        logger.info(
            "Analysis: %d modules, %d patterns, %d interfaces in %.0fms",
            len(modules),
            len(patterns),
            len(interfaces),
            _elapsed_ms(t3),
        )

        provider = None
        if config.enrich and config.provider:
            provider = get_provider(config.provider, config.provider_config)

        decisions = infer_decisions(patterns, modules, interfaces, provider=provider)

        lang_counts: dict[str, int] = {}
        for f in files:
            lang_counts[f.language] = lang_counts.get(f.language, 0) + 1

        total_lines = sum(pf.lines for pf in parsed_files)

        repo_metadata = RepoMetadata(
            url=url,
            local_path=local_path,
            languages=lang_counts,
            total_files=len(files),
            total_lines=total_lines,
        )

        profile = build_profile(
            repo_metadata,
            parsed_files,
            graph,
            modules=modules,
            patterns=patterns,
            interfaces=interfaces,
            decisions=decisions,
        )
        logger.info("analyze() completed in %.0fms", _elapsed_ms(t0))
        return profile
    finally:
        cleanup()


def query(
    source: RepoSource,
    question: str,
    token_budget: int = 8192,
    config: Config | None = None,
    index_config: IndexConfig | None = None,
    scoring_weights: ScoringWeights | None = None,
    chunker: Chunker | None = None,
) -> ContextBundle:
    """Retrieve a ranked ContextBundle for a natural-language query.

    Runs the full pipeline: acquire → parse → chunk → index → search → assemble.
    On cache hit, skips the full parse: loads chunks and graph from the cached store.
    """
    if config is None:
        config = Config()
    if index_config is None:
        index_config = IndexConfig()

    t0 = time.perf_counter()
    cache = CacheManager(cache_dir=config.cache_dir)
    cache_key = cache.cache_key(source)

    # Check cache BEFORE parsing — if cached, skip the expensive parse pipeline
    cached_db = cache.get(cache_key) if config.cache else None
    if cached_db is not None:
        logger.info("Cache hit for %s", cache_key[:12])
        store = IndexStore(cached_db)
        if store.needs_reindex():
            logger.info("Stale cache (missing symbol_ids) — forcing full re-index")
            store.close()
            cache.invalidate(cache_key)
            cached_db = None
        else:
            try:
                bm25 = BM25Index(store)
                cached_chunks = store.get_chunks()
                if cached_chunks:
                    bm25.build(cached_chunks)
                stored_edges = store.get_edges()
                graph = DependencyGraph.from_edges(stored_edges)

                vector_results: list[tuple[object, float]] | None = None
                if index_config.vector:
                    vec_path = cache.vector_path(cache_key)
                    if vec_path.exists():
                        from archex.index.vector import VectorIndex

                        vec_idx = VectorIndex()
                        vec_idx.load(vec_path, cached_chunks)
                        embedder = _get_embedder(index_config)
                        if embedder is not None:
                            vector_results = vec_idx.search(question, embedder, top_k=50)  # type: ignore[assignment]

                search_results = bm25.search(question, top_k=50)
                bundle = assemble_context(
                    search_results=search_results,
                    graph=graph,
                    all_chunks=cached_chunks,
                    question=question,
                    token_budget=token_budget,
                    vector_results=vector_results,  # type: ignore[arg-type]
                    scoring_weights=scoring_weights,
                )
                logger.info("query() [cached] completed in %.0fms", _elapsed_ms(t0))
                return bundle
            finally:
                store.close()

    # Cache miss — full pipeline
    logger.info("Cache miss — running full pipeline")
    t1 = time.perf_counter()
    repo_path, _url, _local_path, cleanup = _acquire(source)
    logger.info("Acquired repo in %.0fms", _elapsed_ms(t1))
    try:
        t2 = time.perf_counter()
        files = discover_files(
            repo_path, languages=config.languages, max_file_size=config.max_file_size
        )
        logger.info("Discovered %d files in %.0fms", len(files), _elapsed_ms(t2))

        engine = TreeSitterEngine()
        adapters = _build_adapters()

        t3 = time.perf_counter()
        parsed_files = extract_symbols(files, engine, adapters, parallel=config.parallel)
        import_map = parse_imports(files, engine, adapters, parallel=config.parallel)
        file_map = build_file_map(files)
        file_languages = {f.path: f.language for f in files}
        resolved_map = resolve_imports(import_map, file_map, adapters, file_languages)
        logger.info("Parsed %d files in %.0fms", len(parsed_files), _elapsed_ms(t3))

        graph = DependencyGraph.from_parsed_files(parsed_files, resolved_map)

        t4 = time.perf_counter()
        file_chunker: Chunker = chunker if chunker is not None else ASTChunker(config=index_config)
        sources: dict[str, bytes] = {}
        for f in files:
            try:
                sources[f.path] = Path(f.absolute_path).read_bytes()
            except OSError:
                continue
        all_chunks = file_chunker.chunk_files(parsed_files, sources)
        logger.info("Chunked into %d chunks in %.0fms", len(all_chunks), _elapsed_ms(t4))

        db_path = Path(tempfile.mkdtemp()) / "index.db"
        store = IndexStore(db_path)

        try:
            bm25 = BM25Index(store)
            store.insert_chunks(all_chunks)
            edges = graph.file_edges()
            store.insert_edges(edges)
            bm25.build(all_chunks)

            # Build vector index if configured
            vector_results_miss: list[tuple[object, float]] | None = None
            if index_config.vector:
                embedder = _get_embedder(index_config)
                if embedder is not None:
                    from archex.index.vector import VectorIndex

                    t5 = time.perf_counter()
                    vec_idx = VectorIndex()
                    vec_idx.build(all_chunks, embedder)  # type: ignore[arg-type]
                    vector_results_miss = vec_idx.search(question, embedder, top_k=50)  # type: ignore[assignment]
                    logger.info("Vector index built in %.0fms", _elapsed_ms(t5))

                    if config.cache:
                        vec_idx.save(cache.vector_path(cache_key))

            if config.cache:
                store.conn.execute("PRAGMA wal_checkpoint(FULL)")
                cache.put(cache_key, db_path)

            t6 = time.perf_counter()
            search_results = bm25.search(question, top_k=50)
            bundle = assemble_context(
                search_results=search_results,
                graph=graph,
                all_chunks=all_chunks,
                question=question,
                token_budget=token_budget,
                vector_results=vector_results_miss,  # type: ignore[arg-type]
                scoring_weights=scoring_weights,
            )
            logger.info("Search + assemble in %.0fms", _elapsed_ms(t6))
        finally:
            store.close()

        logger.info("query() completed in %.0fms", _elapsed_ms(t0))
        return bundle
    finally:
        cleanup()


def _get_embedder(index_config: IndexConfig) -> object | None:
    """Create an embedder from index_config, or return None if not configured."""
    if not index_config.embedder:
        return None
    if index_config.embedder == "nomic":
        from archex.index.embeddings.nomic import NomicCodeEmbedder

        return NomicCodeEmbedder()
    if index_config.embedder == "sentence_transformers":
        from archex.index.embeddings.sentence_tf import SentenceTransformerEmbedder

        return SentenceTransformerEmbedder()
    # API embedder requires additional config — not created here
    return None


def compare(
    source_a: RepoSource,
    source_b: RepoSource,
    dimensions: list[str] | None = None,
    config: Config | None = None,
) -> ComparisonResult:
    """Analyze two repositories and return a ComparisonResult.

    Uses ThreadPoolExecutor to run both analyses concurrently.
    """
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_a = executor.submit(analyze, source_a, config)
        future_b = executor.submit(analyze, source_b, config)
        profile_a = future_a.result()
        profile_b = future_b.result()
    return compare_repos(profile_a, profile_b, dimensions)


# ---------------------------------------------------------------------------
# Tier 1 — Precision Symbol Tools
# ---------------------------------------------------------------------------


def file_tree(
    source: RepoSource,
    max_depth: int = 5,
    language: str | None = None,
    config: Config | None = None,
) -> FileTree:
    """Return the annotated file structure of an indexed repository."""
    store = _ensure_index(source, config)
    try:
        file_meta = store.get_file_metadata()
    finally:
        store.close()

    # Filter by language if requested
    if language:
        file_meta = [m for m in file_meta if m["language"] == language]

    # Build hierarchical tree from flat file paths
    lang_counts: dict[str, int] = {}
    root_entries: dict[str, FileTreeEntry] = {}

    for meta in file_meta:
        fp = str(meta["file_path"])
        lang = str(meta["language"])
        lang_counts[lang] = lang_counts.get(lang, 0) + 1

        parts = fp.split("/")
        # Walk/create directory entries
        current_level = root_entries
        for i, part in enumerate(parts[:-1]):
            if i >= max_depth:
                break
            if part not in current_level:
                dir_path = "/".join(parts[: i + 1])
                current_level[part] = FileTreeEntry(path=dir_path, is_directory=True)
            entry = current_level[part]
            # Build a child dict from the children list for lookup
            child_map = {c.path.split("/")[-1]: c for c in entry.children}
            current_level = child_map  # type: ignore[assignment]
            # Ensure the next level exists in children
            if i + 1 < len(parts) - 1:
                next_part = parts[i + 1]
                if next_part not in current_level:
                    next_path = "/".join(parts[: i + 2])
                    new_child = FileTreeEntry(path=next_path, is_directory=True)
                    entry.children.append(new_child)
                    current_level[next_part] = new_child  # type: ignore[assignment]

        # Add the file entry
        if len(parts) - 1 < max_depth:
            file_entry = FileTreeEntry(
                path=fp,
                language=lang,
                lines=int(meta["lines"]),
                symbol_count=int(meta["symbol_count"]),
                is_directory=False,
            )
            if len(parts) == 1:
                root_entries[parts[0]] = file_entry
            else:
                _add_file_to_tree(root_entries, parts, file_entry)

    entries = sorted(root_entries.values(), key=lambda e: (not e.is_directory, e.path))

    return FileTree(
        root=source.local_path or source.url or "",
        entries=entries,
        total_files=len(file_meta),
        languages=lang_counts,
    )


def _add_file_to_tree(
    root_entries: dict[str, FileTreeEntry],
    parts: list[str],
    file_entry: FileTreeEntry,
) -> None:
    """Walk the tree and add a file entry under its parent directory."""
    if parts[0] not in root_entries:
        dir_path = parts[0]
        root_entries[parts[0]] = FileTreeEntry(path=dir_path, is_directory=True)

    current = root_entries[parts[0]]
    for part in parts[1:-1]:
        found = False
        for child in current.children:
            if child.path.split("/")[-1] == part:
                current = child
                found = True
                break
        if not found:
            return

    # Avoid duplicate file entries
    existing_paths = {c.path for c in current.children}
    if file_entry.path not in existing_paths:
        current.children.append(file_entry)


def file_outline(
    source: RepoSource,
    file_path: str,
    config: Config | None = None,
) -> FileOutline:
    """Return the symbol hierarchy for a single file — no source code."""
    store = _ensure_index(source, config)
    try:
        chunks = store.get_chunks_for_file(file_path)
    finally:
        store.close()

    if not chunks:
        return FileOutline(
            file_path=file_path,
            language="unknown",
            lines=0,
            symbols=[],
            token_count_raw=0,
        )

    language = chunks[0].language
    max_line = max(c.end_line for c in chunks)
    token_count_raw = sum(c.token_count for c in chunks)

    # Build flat outlines
    outlines = [_chunk_to_symbol_outline(c) for c in chunks]

    # Reconstruct parent-child hierarchy from qualified_name
    top_level: list[SymbolOutline] = []
    by_qname: dict[str, SymbolOutline] = {}

    for outline in outlines:
        qname = outline.name
        chunk = next((c for c in chunks if (c.symbol_id or c.id) == outline.symbol_id), None)
        if chunk and chunk.qualified_name:
            qname = chunk.qualified_name
        by_qname[qname] = outline

    for outline in outlines:
        chunk = next((c for c in chunks if (c.symbol_id or c.id) == outline.symbol_id), None)
        qname = chunk.qualified_name if chunk and chunk.qualified_name else outline.name
        # Check if this is a child (has a dot separator indicating parent.child)
        parent_name = _get_parent_qname(qname)
        if parent_name and parent_name in by_qname:
            by_qname[parent_name].children.append(outline)
        else:
            top_level.append(outline)

    return FileOutline(
        file_path=file_path,
        language=language,
        lines=max_line,
        symbols=top_level,
        token_count_raw=token_count_raw,
    )


def _get_parent_qname(qualified_name: str) -> str | None:
    """Extract the parent's qualified name from a dotted or :: separated name."""
    if "::" in qualified_name:
        parts = qualified_name.rsplit("::", 1)
        return parts[0] if len(parts) > 1 else None
    if "." in qualified_name:
        parts = qualified_name.rsplit(".", 1)
        return parts[0] if len(parts) > 1 else None
    return None


def search_symbols(
    source: RepoSource,
    query: str,
    kind: str | None = None,
    language: str | None = None,
    limit: int = 20,
    config: Config | None = None,
) -> list[SymbolMatch]:
    """Search symbols by name across the indexed repository."""
    store = _ensure_index(source, config)
    try:
        sym_kind = SymbolKind(kind) if kind else None
        chunks = store.search_symbols(query, kind=sym_kind, limit=limit)
    finally:
        store.close()

    if language:
        chunks = [c for c in chunks if c.language == language]

    return [_chunk_to_symbol_match(c) for c in chunks[:limit]]


def get_symbol(
    source: RepoSource,
    symbol_id: str,
    config: Config | None = None,
) -> SymbolSource | None:
    """Retrieve the full source code of a single symbol by its stable ID."""
    store = _ensure_index(source, config)
    try:
        chunk = store.get_chunk_by_symbol_id(symbol_id)
    finally:
        store.close()

    if chunk is None:
        return None
    return _chunk_to_symbol_source(chunk)


def get_symbols_batch(
    source: RepoSource,
    symbol_ids: list[str],
    config: Config | None = None,
) -> list[SymbolSource | None]:
    """Batch retrieve N symbols by their stable IDs. Preserves input order."""
    if len(symbol_ids) > 50:
        raise ValueError(f"Maximum 50 symbol IDs per batch, got {len(symbol_ids)}")

    store = _ensure_index(source, config)
    try:
        chunks = store.get_chunks_by_symbol_ids(symbol_ids)
    finally:
        store.close()

    # Preserve input order: build lookup by symbol_id, map back
    by_sid: dict[str, CodeChunk] = {c.symbol_id: c for c in chunks if c.symbol_id}
    return [_chunk_to_symbol_source(by_sid[sid]) if sid in by_sid else None for sid in symbol_ids]
