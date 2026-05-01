"""Tests for CORE/engines/quality_gate.py — Feature 3"""

from __future__ import annotations

import pytest

from CORE.engines.quality_gate import DEFAULT_THRESHOLDS, QualityGate


@pytest.fixture
def gate():
    return QualityGate()


@pytest.fixture
def strict_gate():
    return QualityGate(
        config={"quality_gate": {"max_high": 0, "max_medium": 0, "max_total": 5, "max_security": 0, "mode": "block"}}
    )


@pytest.fixture
def warn_gate():
    return QualityGate(config={"quality_gate": {"mode": "warn", "max_high": 0}})


def _finding(sev="low", cat="style", rule="STYLE-001"):
    return {"canonical_severity": sev, "category": cat, "canonical_rule_id": rule}


class TestQualityGateInit:
    def test_defaults_loaded(self, gate):
        assert gate.thresholds["max_high"] == DEFAULT_THRESHOLDS["max_high"]

    def test_config_overrides_defaults(self, strict_gate):
        assert strict_gate.thresholds["max_medium"] == 0

    def test_none_config_uses_defaults(self):
        g = QualityGate(config=None)
        assert g.thresholds["mode"] == "block"

    def test_empty_config_uses_defaults(self):
        g = QualityGate(config={})
        assert g.thresholds["max_high"] == 0

    def test_config_without_quality_gate_key(self):
        g = QualityGate(config={"rules": {"enabled": True}})
        assert g.thresholds["max_high"] == DEFAULT_THRESHOLDS["max_high"]


class TestEvaluateCounts:
    def test_empty_findings_passes(self, gate):
        result = gate.evaluate([])
        assert result["passed"] is True
        assert result["counts"]["total"] == 0

    def test_counts_severity_correctly(self, gate):
        findings = [_finding("high"), _finding("medium"), _finding("low"), _finding("low")]
        result = gate.evaluate(findings)
        assert result["counts"]["high"] == 1
        assert result["counts"]["medium"] == 1
        assert result["counts"]["low"] == 2
        assert result["counts"]["total"] == 4

    def test_counts_category_correctly(self, gate):
        findings = [_finding(cat="security"), _finding(cat="security"), _finding(cat="style")]
        result = gate.evaluate(findings)
        assert result["category_counts"]["security"] == 2
        assert result["category_counts"]["style"] == 1

    def test_severity_fallback_key(self, gate):
        f = {"severity": "high", "category": "security"}
        result = gate.evaluate([f])
        assert result["counts"]["high"] == 1

    def test_unknown_severity_counted_in_totals(self, gate):
        f = {"canonical_severity": "banana", "category": "style"}
        result = gate.evaluate([f])
        assert result["counts"]["total"] == 1


class TestEvaluateChecks:
    def test_fails_on_high_severity_exceeding_max(self, strict_gate):
        result = strict_gate.evaluate([_finding("high", "security")])
        assert result["passed"] is False

    def test_fails_on_medium_exceeding_max(self, strict_gate):
        findings = [_finding("medium") for _ in range(5)]
        result = strict_gate.evaluate(findings)
        assert result["passed"] is False

    def test_fails_on_total_exceeding_max(self, strict_gate):
        findings = [_finding("low") for _ in range(10)]
        result = strict_gate.evaluate(findings)
        assert result["passed"] is False

    def test_fails_on_security_exceeding_max(self, strict_gate):
        result = strict_gate.evaluate([_finding("low", "security")])
        assert result["passed"] is False

    def test_passes_within_all_thresholds(self):
        g = QualityGate(config={"quality_gate": {"max_high": 1, "max_medium": 5, "max_total": 10, "max_security": 2}})
        findings = [_finding("high", "security"), _finding("medium"), _finding("low")]
        result = g.evaluate(findings)
        assert result["passed"] is True

    def test_checks_list_has_four_items(self, gate):
        result = gate.evaluate([])
        assert len(result["checks"]) == 4

    def test_all_checks_passed_when_empty(self, gate):
        result = gate.evaluate([])
        assert all(c["passed"] for c in result["checks"])

    def test_status_passed_string(self, gate):
        result = gate.evaluate([])
        assert "PASSED" in result["status"]

    def test_status_failed_string(self, strict_gate):
        result = strict_gate.evaluate([_finding("high", "security")])
        assert "FAILED" in result["status"]

    def test_summary_mentions_checks(self, gate):
        result = gate.evaluate([])
        assert "checks" in result["summary"].lower()


class TestShouldBlock:
    def test_block_mode_blocks_on_failure(self, strict_gate):
        result = strict_gate.evaluate([_finding("high", "security")])
        assert strict_gate.should_block(result) is True

    def test_block_mode_does_not_block_on_pass(self, gate):
        result = gate.evaluate([])
        assert gate.should_block(result) is False

    def test_warn_mode_never_blocks(self, warn_gate):
        result = warn_gate.evaluate([_finding("high", "security")])
        assert warn_gate.should_block(result) is False

    def test_warn_mode_never_blocks_even_on_fail(self):
        g = QualityGate(config={"quality_gate": {"mode": "warn", "max_high": 0, "max_total": 1}})
        findings = [_finding("high") for _ in range(10)]
        result = g.evaluate(findings)
        assert g.should_block(result) is False


class TestFormatGateComment:
    def test_returns_string(self, gate):
        result = gate.evaluate([])
        comment = gate.format_gate_comment(result)
        assert isinstance(comment, str)

    def test_contains_passed_status(self, gate):
        result = gate.evaluate([])
        comment = gate.format_gate_comment(result)
        assert "PASSED" in comment

    def test_contains_failed_status(self, strict_gate):
        result = strict_gate.evaluate([_finding("high", "security")])
        comment = strict_gate.format_gate_comment(result)
        assert "FAILED" in comment

    def test_block_mode_mentions_merge_blocked(self, strict_gate):
        result = strict_gate.evaluate([_finding("high", "security")])
        comment = strict_gate.format_gate_comment(result)
        assert "blocked" in comment.lower()

    def test_warn_mode_mentions_warn(self, warn_gate):
        result = warn_gate.evaluate([_finding("high", "security")])
        comment = warn_gate.format_gate_comment(result)
        assert "warn" in comment.lower() or "Warn" in comment

    def test_contains_severity_table(self, gate):
        result = gate.evaluate([_finding("high"), _finding("medium")])
        comment = gate.format_gate_comment(result)
        assert "High" in comment and "Medium" in comment

    def test_passed_gate_mentions_safe_to_merge(self, gate):
        result = gate.evaluate([])
        comment = gate.format_gate_comment(result)
        assert "safe" in comment.lower() or "passed" in comment.lower()


class TestPrintReport:
    def test_print_report_does_not_crash(self, gate, caplog):
        import logging

        caplog.set_level(logging.INFO)
        result = gate.evaluate([_finding("high"), _finding("medium"), _finding("low")])
        gate.print_report(result)
        assert "Quality Gate" in caplog.text

    def test_print_report_failed_gate(self, strict_gate, caplog):
        import logging

        caplog.set_level(logging.INFO)
        result = strict_gate.evaluate([_finding("high", "security")])
        strict_gate.print_report(result)
        assert "FAILED" in caplog.text
