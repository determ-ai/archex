"""Tests for F1 and MRR metric functions."""

from __future__ import annotations

from archex.benchmark.strategies import compute_f1, compute_mrr


def test_compute_f1_perfect() -> None:
    assert compute_f1(1.0, 1.0) == 1.0


def test_compute_f1_zero() -> None:
    assert compute_f1(0.0, 0.0) == 0.0


def test_compute_f1_typical() -> None:
    f1 = compute_f1(0.8, 0.6)
    expected = 2 * (0.8 * 0.6) / (0.8 + 0.6)
    assert abs(f1 - expected) < 1e-9


def test_compute_mrr_first_match() -> None:
    assert compute_mrr(["a.py", "b.py", "c.py"], ["a.py"]) == 1.0


def test_compute_mrr_third_match() -> None:
    result = compute_mrr(["x.py", "y.py", "a.py"], ["a.py"])
    assert abs(result - 1 / 3) < 1e-9


def test_compute_mrr_no_match() -> None:
    assert compute_mrr(["x.py", "y.py"], ["a.py"]) == 0.0
