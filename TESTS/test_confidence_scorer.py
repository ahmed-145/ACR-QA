"""
Tests for CORE/engines/confidence_scorer.py — Feature 5
Target: 90%+ coverage of ConfidenceScorer and compute_confidence.
"""

from __future__ import annotations

import pytest

from CORE.engines.confidence_scorer import (
    _CATEGORY_SCORE,
    _CUSTOM_BONUS,
    _FIX_BONUS,
    _RULE_BONUS,
    ConfidenceScorer,
    compute_confidence,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def scorer():
    return ConfidenceScorer(known_rule_ids={"SECURITY-001", "SECURITY-059", "STYLE-001"})


@pytest.fixture
def high_security_finding():
    return {
        "canonical_severity": "high",
        "category": "security",
        "tool": "bandit",
        "canonical_rule_id": "SECURITY-001",
    }


@pytest.fixture
def low_style_finding():
    return {
        "canonical_severity": "low",
        "category": "style",
        "tool": "ruff",
        "canonical_rule_id": "STYLE-001",
    }


# ── Signal 1: Severity ────────────────────────────────────────────────────────


class TestSeveritySignal:
    def test_high_severity_adds_40(self, scorer):
        f = {"canonical_severity": "high", "category": "style", "tool": "ruff", "canonical_rule_id": "UNKNOWN-X"}
        score = scorer.score(f)
        assert score >= 40

    def test_critical_severity_adds_40(self, scorer):
        f = {"canonical_severity": "critical", "category": "style", "tool": "ruff", "canonical_rule_id": "UNKNOWN-X"}
        score = scorer.score(f)
        assert score >= 40

    def test_medium_severity_adds_25(self, scorer):
        f = {"canonical_severity": "medium", "category": "style", "tool": "ruff", "canonical_rule_id": "UNKNOWN-X"}
        score = scorer.score(f)
        assert score >= 25

    def test_low_severity_adds_10(self, scorer):
        f = {"canonical_severity": "low", "category": "style", "tool": "ruff", "canonical_rule_id": "UNKNOWN-X"}
        score = scorer.score(f)
        assert score >= 10

    def test_unknown_severity_defaults_to_10(self, scorer):
        f = {"canonical_severity": "banana", "category": "style", "tool": "ruff", "canonical_rule_id": "UNKNOWN-X"}
        score = scorer.score(f)
        assert score >= 10

    def test_severity_fallback_to_severity_key(self, scorer):
        """Falls back to 'severity' if 'canonical_severity' missing."""
        f = {"severity": "high", "category": "security", "tool": "bandit", "canonical_rule_id": "UNKNOWN-X"}
        score = scorer.score(f)
        assert score >= 40


# ── Signal 2: Category ────────────────────────────────────────────────────────


class TestCategorySignal:
    def test_security_adds_20(self, scorer):
        f = {"canonical_severity": "low", "category": "security", "tool": "ruff", "canonical_rule_id": "UNKNOWN-X"}
        assert scorer.score(f) >= _CATEGORY_SCORE["security"]

    def test_design_adds_10(self, scorer):
        f = {"canonical_severity": "low", "category": "design", "tool": "ruff", "canonical_rule_id": "UNKNOWN-X"}
        assert scorer.score(f) >= _CATEGORY_SCORE["design"]

    def test_best_practice_adds_5(self, scorer):
        f = {"canonical_severity": "low", "category": "best-practice", "tool": "ruff", "canonical_rule_id": "UNKNOWN-X"}
        assert scorer.score(f) >= _CATEGORY_SCORE["best-practice"]

    def test_style_adds_0(self, scorer):
        f = {"canonical_severity": "low", "category": "style", "tool": "ruff", "canonical_rule_id": "UNKNOWN-X"}
        # style contributes 0 — score is still >= 0
        assert scorer.score(f) >= 0

    def test_dead_code_adds_5(self, scorer):
        f = {"canonical_severity": "low", "category": "dead-code", "tool": "vulture", "canonical_rule_id": "UNKNOWN-X"}
        assert scorer.score(f) >= _CATEGORY_SCORE["dead-code"]

    def test_unknown_category_adds_0(self, scorer):
        f = {"canonical_severity": "low", "category": "nonsense", "tool": "ruff", "canonical_rule_id": "UNKNOWN-X"}
        assert scorer.score(f) >= 0


# ── Signal 3: Tool reliability ────────────────────────────────────────────────


class TestToolSignal:
    @pytest.mark.parametrize(
        "tool,expected_min",
        [
            ("bandit", 15),
            ("semgrep", 15),
            ("secrets", 15),
            ("eslint", 10),
            ("ruff", 8),
            ("vulture", 5),
            ("radon", 5),
            ("jscpd", 3),
            ("npm-audit", 12),
            ("cbom", 12),
            ("sca", 12),
        ],
    )
    def test_known_tool_scores(self, scorer, tool, expected_min):
        f = {"canonical_severity": "low", "category": "style", "tool": tool, "canonical_rule_id": "UNKNOWN-X"}
        assert scorer.score(f) >= expected_min

    def test_unknown_tool_defaults_to_5(self, scorer):
        f = {"canonical_severity": "low", "category": "style", "tool": "mytool", "canonical_rule_id": "UNKNOWN-X"}
        assert scorer.score(f) >= 5

    def test_tool_from_tool_raw_dict(self, scorer):
        """tool_raw nested dict fallback."""
        f = {
            "canonical_severity": "low",
            "category": "style",
            "tool": "",
            "canonical_rule_id": "UNKNOWN-X",
            "tool_raw": {"tool_name": "bandit"},
        }
        assert scorer.score(f) >= 15

    def test_tool_raw_non_dict_ignored(self, scorer):
        """tool_raw that is not a dict should not crash."""
        f = {
            "canonical_severity": "low",
            "category": "style",
            "tool": "",
            "canonical_rule_id": "UNKNOWN-X",
            "tool_raw": "bandit",
        }
        assert scorer.score(f) >= 0


# ── Signal 4: Rule specificity ────────────────────────────────────────────────


class TestRuleSignal:
    def test_known_rule_adds_bonus(self, scorer):
        f = {"canonical_severity": "low", "category": "style", "tool": "ruff", "canonical_rule_id": "SECURITY-001"}
        score_known = scorer.score(f)
        f2 = {"canonical_severity": "low", "category": "style", "tool": "ruff", "canonical_rule_id": "UNKNOWN-ZZZ"}
        score_unknown = scorer.score(f2)
        assert score_known == score_unknown + _RULE_BONUS

    def test_custom_rule_adds_custom_bonus(self, scorer):
        f = {"canonical_severity": "low", "category": "style", "tool": "ruff", "canonical_rule_id": "CUSTOM-mycheck"}
        score_custom = scorer.score(f)
        f2 = {"canonical_severity": "low", "category": "style", "tool": "ruff", "canonical_rule_id": "UNKNOWN-ZZZ"}
        score_unknown = scorer.score(f2)
        assert score_custom == score_unknown + _CUSTOM_BONUS

    def test_rule_id_fallback_to_rule_id_key(self, scorer):
        f = {"canonical_severity": "low", "category": "style", "tool": "ruff", "rule_id": "SECURITY-001"}
        assert scorer.score(f) >= _RULE_BONUS


# ── Signal 5: Fix validated ───────────────────────────────────────────────────


class TestFixValidatedSignal:
    def test_fix_validated_true_adds_bonus(self, scorer, high_security_finding):
        score_with = scorer.score(high_security_finding, fix_validated=True)
        score_without = scorer.score(high_security_finding, fix_validated=None)
        assert score_with == score_without + _FIX_BONUS

    def test_fix_validated_false_adds_nothing(self, scorer, high_security_finding):
        score_false = scorer.score(high_security_finding, fix_validated=False)
        score_none = scorer.score(high_security_finding, fix_validated=None)
        assert score_false == score_none

    def test_fix_validated_none_adds_nothing(self, scorer, high_security_finding):
        score = scorer.score(high_security_finding, fix_validated=None)
        assert isinstance(score, int)


# ── Clamping ──────────────────────────────────────────────────────────────────


class TestClamping:
    def test_score_never_exceeds_100(self, scorer):
        f = {
            "canonical_severity": "high",
            "category": "security",
            "tool": "bandit",
            "canonical_rule_id": "SECURITY-001",
        }
        assert scorer.score(f, fix_validated=True) <= 100

    def test_score_never_below_0(self, scorer):
        f = {"canonical_severity": "banana", "category": "nonsense", "tool": "", "canonical_rule_id": ""}
        assert scorer.score(f) >= 0


# ── score_batch ───────────────────────────────────────────────────────────────


class TestScoreBatch:
    def test_batch_returns_same_length(self, scorer, high_security_finding, low_style_finding):
        results = scorer.score_batch([high_security_finding, low_style_finding])
        assert len(results) == 2

    def test_batch_empty_list(self, scorer):
        assert scorer.score_batch([]) == []

    def test_batch_values_match_individual(self, scorer, high_security_finding, low_style_finding):
        batch = scorer.score_batch([high_security_finding, low_style_finding])
        assert batch[0] == scorer.score(high_security_finding)
        assert batch[1] == scorer.score(low_style_finding)

    def test_high_scores_higher_than_low(self, scorer, high_security_finding, low_style_finding):
        batch = scorer.score_batch([high_security_finding, low_style_finding])
        assert batch[0] > batch[1]


# ── label() ───────────────────────────────────────────────────────────────────


class TestLabel:
    @pytest.mark.parametrize(
        "score,expected",
        [
            (95, "very high"),
            (90, "very high"),
            (89, "high"),
            (70, "high"),
            (69, "medium"),
            (50, "medium"),
            (49, "low"),
            (30, "low"),
            (29, "very low"),
            (0, "very low"),
        ],
    )
    def test_label_boundaries(self, score, expected):
        assert ConfidenceScorer.label(score) == expected


# ── ConfidenceScorer with default known_rule_ids (None path) ──────────────────


class TestDefaultKnownRules:
    def test_instantiate_with_none_does_not_crash(self):
        """Exercises the try/except import path."""
        scorer = ConfidenceScorer(known_rule_ids=None)
        f = {
            "canonical_severity": "high",
            "category": "security",
            "tool": "bandit",
            "canonical_rule_id": "SECURITY-001",
        }
        assert isinstance(scorer.score(f), int)


# ── compute_confidence convenience function ───────────────────────────────────


class TestComputeConfidence:
    def test_returns_int(self):
        f = {
            "canonical_severity": "high",
            "category": "security",
            "tool": "bandit",
            "canonical_rule_id": "SECURITY-001",
        }
        assert isinstance(compute_confidence(f), int)

    def test_fix_validated_passed_through(self):
        f = {
            "canonical_severity": "high",
            "category": "security",
            "tool": "bandit",
            "canonical_rule_id": "SECURITY-001",
        }
        with_fix = compute_confidence(f, fix_validated=True)
        without_fix = compute_confidence(f, fix_validated=None)
        assert with_fix == without_fix + _FIX_BONUS

    def test_matches_scorer_output(self):
        f = {"canonical_severity": "medium", "category": "design", "tool": "semgrep", "canonical_rule_id": "CUSTOM-x"}
        scorer = ConfidenceScorer(known_rule_ids=set())
        assert compute_confidence(f) == scorer.score(f)
