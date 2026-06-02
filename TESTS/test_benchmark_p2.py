"""
Tests for scripts/run_benchmark_p2.py — the rigorous benchmark harness.
Covers the statistics (MCC, bootstrap CI), path matching, and corpus loading.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

# Load the script as a module (it lives in scripts/, not a package)
_SPEC = importlib.util.spec_from_file_location(
    "run_benchmark_p2",
    Path(__file__).parent.parent / "scripts" / "run_benchmark_p2.py",
)
p2 = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(p2)


class TestMCC:
    def test_perfect_classifier(self):
        # tp, tn, fp, fn — perfect → MCC 1.0
        assert p2.mcc(10, 10, 0, 0) == pytest.approx(1.0)

    def test_worst_classifier(self):
        # all wrong → MCC -1.0
        assert p2.mcc(0, 0, 10, 10) == pytest.approx(-1.0)

    def test_zero_denominator(self):
        # degenerate (all one class predicted) → 0.0, no crash
        assert p2.mcc(10, 0, 0, 0) == 0.0

    def test_random_classifier_near_zero(self):
        val = p2.mcc(5, 5, 5, 5)
        assert val == pytest.approx(0.0)


class TestBootstrapCI:
    def test_all_correct_recall(self):
        labels = [1] * 20
        preds = [1] * 20
        lo, hi = p2.bootstrap_ci(labels, preds, "recall")
        assert lo == pytest.approx(1.0)
        assert hi == pytest.approx(1.0)

    def test_half_recall_band(self):
        labels = [1] * 20
        preds = [1] * 10 + [0] * 10
        lo, hi = p2.bootstrap_ci(labels, preds, "recall")
        assert 0.2 < lo < 0.5
        assert 0.5 < hi < 0.8

    def test_empty(self):
        assert p2.bootstrap_ci([], [], "recall") == (0.0, 0.0)

    def test_deterministic_seed(self):
        labels = [1, 0, 1, 0, 1, 1, 0, 1]
        preds = [1, 0, 1, 1, 1, 0, 0, 1]
        r1 = p2.bootstrap_ci(labels, preds, "precision")
        r2 = p2.bootstrap_ci(labels, preds, "precision")
        assert r1 == r2  # seeded → reproducible


class TestPathMatching:
    def test_exact_match(self):
        assert p2._flagged_match({"/a/b/c.py"}, "/a/b/c.py") is True

    def test_suffix_match(self):
        assert p2._flagged_match({"/abs/path/CWE-089/author_1.py"}, "CWE-089/author_1.py") is True

    def test_no_match(self):
        assert p2._flagged_match({"/a/x.py"}, "/a/y.py") is False

    def test_empty_flagged(self):
        assert p2._flagged_match(set(), "/a/b.py") is False


class TestScoreRecall:
    def test_full_detection(self):
        corpus = {"/c/CWE-089/a.py": "CWE-089", "/c/CWE-078/b.py": "CWE-078"}
        flagged = {"/c/CWE-089/a.py", "/c/CWE-078/b.py"}
        r = p2.score_recall(corpus, flagged)
        assert r["recall"] == 100.0
        assert r["tp"] == 2
        assert r["fn"] == 0

    def test_partial_detection(self):
        corpus = {"/c/CWE-089/a.py": "CWE-089", "/c/CWE-078/b.py": "CWE-078"}
        flagged = {"/c/CWE-089/a.py"}
        r = p2.score_recall(corpus, flagged)
        assert r["recall"] == 50.0
        assert r["tp"] == 1
        assert r["fn"] == 1

    def test_per_cwe_breakdown(self):
        corpus = {"/c/CWE-089/a.py": "CWE-089", "/c/CWE-089/b.py": "CWE-089"}
        flagged = {"/c/CWE-089/a.py"}
        r = p2.score_recall(corpus, flagged)
        assert r["per_cwe"]["CWE-089"]["total"] == 2
        assert r["per_cwe"]["CWE-089"]["hit"] == 1


class TestDetectableSet:
    def test_contains_injection_cwes(self):
        for cwe in ("CWE-078", "CWE-089", "CWE-502", "CWE-611", "CWE-918"):
            assert cwe in p2.STATICALLY_DETECTABLE

    def test_excludes_authz_cwes(self):
        # Authorization/session/logic CWEs are not statically detectable
        for cwe in ("CWE-285", "CWE-306", "CWE-352", "CWE-384"):
            assert cwe not in p2.STATICALLY_DETECTABLE
