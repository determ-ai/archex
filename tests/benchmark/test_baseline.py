"""Tests for baseline save/load/compare functionality."""

from __future__ import annotations

from archex.benchmark.baseline import (
    Baseline,
    BaselineEntry,
    compare_baseline,
    load_baseline,
    save_baseline,
)
from archex.benchmark.models import BenchmarkReport, BenchmarkResult, Strategy


def _make_report(
    task_id: str = "test_task",
    recall: float = 0.8,
    precision: float = 0.6,
    f1_score: float = 0.685,
    mrr: float = 0.5,
) -> BenchmarkReport:
    result = BenchmarkResult(
        task_id=task_id,
        strategy=Strategy.ARCHEX_QUERY,
        tokens_total=1000,
        tool_calls=1,
        files_accessed=3,
        recall=recall,
        precision=precision,
        f1_score=f1_score,
        mrr=mrr,
        savings_vs_raw=50.0,
        wall_time_ms=100.0,
        cached=False,
        timestamp="2026-01-01T00:00:00Z",
    )
    return BenchmarkReport(
        task_id=task_id,
        repo="test/repo",
        question="test question",
        results=[result],
        baseline_tokens=2000,
    )


def test_save_load_baseline_roundtrip() -> None:
    reports = [_make_report()]
    baseline = save_baseline(reports)
    assert len(baseline.entries) == 1
    assert baseline.entries[0].task_id == "test_task"

    # Roundtrip through JSON
    data = baseline.model_dump()
    loaded = load_baseline(data)
    assert len(loaded.entries) == 1
    assert loaded.entries[0].recall == 0.8


def test_compare_baseline_detects_regression() -> None:
    baseline = Baseline(
        entries=[
            BaselineEntry(
                task_id="test_task",
                strategy="archex_query",
                recall=0.9,
                precision=0.8,
                f1_score=0.85,
                mrr=0.7,
            )
        ]
    )
    # Current results are worse
    reports = [_make_report(recall=0.5, precision=0.3, f1_score=0.37, mrr=0.2)]
    comparisons = compare_baseline(reports, baseline)
    regressions = [c for c in comparisons if c.regression]
    assert len(regressions) > 0
    regressed_metrics = {c.metric for c in regressions}
    assert "recall" in regressed_metrics


def test_compare_baseline_no_regression() -> None:
    baseline = Baseline(
        entries=[
            BaselineEntry(
                task_id="test_task",
                strategy="archex_query",
                recall=0.8,
                precision=0.6,
                f1_score=0.685,
                mrr=0.5,
            )
        ]
    )
    # Current results are the same or better
    reports = [_make_report(recall=0.85, precision=0.65, f1_score=0.72, mrr=0.55)]
    comparisons = compare_baseline(reports, baseline)
    regressions = [c for c in comparisons if c.regression]
    assert len(regressions) == 0
