"""
ACR-QA Coverage Boost Tests
Targets previously uncovered code paths in:
  - QualityGate (was 8% → target 90%+)
  - SeverityScorer (was 34% → target 85%+)

Covers: CUSTOM-* inference, context adjustments, duplication/complexity
fallback parsing, print_report, DEFAULT_THRESHOLDS, score_severity()
convenience function, and all edge cases.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


# ═════════════════════════════════════════════════════════════════════════════
# QualityGate — Full Coverage
# ═════════════════════════════════════════════════════════════════════════════
class TestQualityGateFullCoverage:
    """Target: push quality_gate.py from 8% → 90%+"""

    def setup_method(self):
        from CORE.engines.quality_gate import QualityGate

        self.QualityGate = QualityGate

    # ── Initialisation ─────────────────────────────────────────────────────

    def test_default_thresholds_loaded(self):
        """DEFAULT_THRESHOLDS must be imported and applied correctly."""
        from CORE.engines.quality_gate import DEFAULT_THRESHOLDS

        gate = self.QualityGate()
        assert gate.thresholds["max_high"] == DEFAULT_THRESHOLDS["max_high"]
        assert gate.thresholds["max_total"] == DEFAULT_THRESHOLDS["max_total"]

    def test_config_none_uses_defaults(self):
        gate = self.QualityGate(None)
        assert "max_high" in gate.thresholds

    def test_config_empty_dict_uses_defaults(self):
        gate = self.QualityGate({})
        assert gate.thresholds["max_high"] == 0

    def test_config_partial_override(self):
        """Only the supplied keys should be overridden."""
        gate = self.QualityGate({"quality_gate": {"max_high": 5}})
        assert gate.thresholds["max_high"] == 5
        # Other defaults preserved
        assert gate.thresholds["max_medium"] == 20

    def test_config_full_override(self):
        config = {
            "quality_gate": {
                "max_high": 2,
                "max_medium": 5,
                "max_total": 50,
                "max_security": 1,
            }
        }
        gate = self.QualityGate(config)
        assert gate.thresholds["max_high"] == 2
        assert gate.thresholds["max_medium"] == 5
        assert gate.thresholds["max_total"] == 50
        assert gate.thresholds["max_security"] == 1

    def test_non_dict_config_ignored(self):
        """config must be dict, otherwise defaults are used."""
        gate = self.QualityGate("not-a-dict")  # type: ignore[arg-type]
        assert gate.thresholds["max_high"] == 0

    # ── evaluate() — PASS scenarios ───────────────────────────────────────

    def test_empty_findings_is_pass(self):
        gate = self.QualityGate(None)
        result = gate.evaluate([])
        assert result["passed"] is True
        assert "PASSED" in result["status"]
        assert result["counts"]["total"] == 0

    def test_all_low_within_limits(self):
        gate = self.QualityGate({"quality_gate": {"max_total": 10}})
        findings = [{"canonical_severity": "low", "category": "style"}] * 5
        assert gate.evaluate(findings)["passed"] is True

    def test_high_at_exact_threshold_passes(self):
        gate = self.QualityGate({"quality_gate": {"max_high": 2}})
        findings = [{"canonical_severity": "high", "category": "security"}] * 2
        assert gate.evaluate(findings)["passed"] is True

    def test_medium_at_exact_threshold_passes(self):
        gate = self.QualityGate({"quality_gate": {"max_medium": 3}})
        findings = [{"canonical_severity": "medium", "category": "design"}] * 3
        assert gate.evaluate(findings)["passed"] is True

    # ── evaluate() — FAIL scenarios ──────────────────────────────────────

    def test_one_high_fails_zero_tolerance(self):
        gate = self.QualityGate({"quality_gate": {"max_high": 0}})
        findings = [{"canonical_severity": "high", "category": "security"}]
        result = gate.evaluate(findings)
        assert result["passed"] is False
        assert "FAILED" in result["status"]

    def test_medium_exceeds_threshold(self):
        gate = self.QualityGate({"quality_gate": {"max_medium": 2}})
        findings = [{"canonical_severity": "medium", "category": "design"}] * 3
        assert gate.evaluate(findings)["passed"] is False

    def test_total_exceeds_threshold(self):
        gate = self.QualityGate({"quality_gate": {"max_total": 2}})
        findings = [{"canonical_severity": "low", "category": "style"}] * 3
        assert gate.evaluate(findings)["passed"] is False

    def test_security_category_exceeds_threshold(self):
        gate = self.QualityGate({"quality_gate": {"max_security": 0}})
        findings = [{"canonical_severity": "low", "category": "security"}]
        assert gate.evaluate(findings)["passed"] is False

    def test_multiple_threshold_failures(self):
        """Both high AND total thresholds exceeded."""
        gate = self.QualityGate({"quality_gate": {"max_high": 0, "max_total": 0}})
        findings = [{"canonical_severity": "high", "category": "security"}]
        result = gate.evaluate(findings)
        assert result["passed"] is False
        failed = [c for c in result["checks"] if not c["passed"]]
        assert len(failed) >= 2

    # ── evaluate() — result structure ────────────────────────────────────

    def test_result_has_all_keys(self):
        gate = self.QualityGate(None)
        result = gate.evaluate([])
        for key in ("passed", "status", "summary", "checks", "counts", "category_counts"):
            assert key in result, f"Missing key: {key}"

    def test_counts_structure(self):
        gate = self.QualityGate(None)
        findings = [
            {"canonical_severity": "high", "category": "security"},
            {"canonical_severity": "medium", "category": "design"},
            {"canonical_severity": "low", "category": "style"},
        ]
        result = gate.evaluate(findings)
        counts = result["counts"]
        assert counts["high"] == 1
        assert counts["medium"] == 1
        assert counts["low"] == 1
        assert counts["total"] == 3

    def test_category_counts(self):
        gate = self.QualityGate(None)
        findings = [
            {"canonical_severity": "high", "category": "security"},
            {"canonical_severity": "high", "category": "security"},
            {"canonical_severity": "medium", "category": "design"},
        ]
        result = gate.evaluate(findings)
        assert result["category_counts"]["security"] == 2
        assert result["category_counts"]["design"] == 1

    def test_checks_list_has_5_items(self):
        gate = self.QualityGate(None)
        result = gate.evaluate([])
        assert len(result["checks"]) == 5

    def test_check_structure(self):
        gate = self.QualityGate(None)
        result = gate.evaluate([])
        for check in result["checks"]:
            assert "name" in check
            assert "passed" in check
            assert "actual" in check
            assert "threshold" in check
            assert "message" in check

    def test_passed_summary_message(self):
        gate = self.QualityGate(None)
        result = gate.evaluate([])
        assert "all" in result["summary"] and "passed" in result["summary"].lower()

    def test_failed_summary_message(self):
        gate = self.QualityGate({"quality_gate": {"max_high": 0}})
        findings = [{"canonical_severity": "high", "category": "security"}]
        result = gate.evaluate(findings)
        assert "failed" in result["summary"].lower()

    def test_severity_fallback_uses_severity_key(self):
        """Finding with 'severity' key (not canonical_severity) should still count."""
        gate = self.QualityGate({"quality_gate": {"max_high": 0}})
        findings = [{"severity": "high", "category": "security"}]
        result = gate.evaluate(findings)
        assert result["counts"]["high"] == 1

    def test_unknown_severity_counted_as_extra(self):
        """Totally unknown severity value should not crash."""
        gate = self.QualityGate(None)
        findings = [{"canonical_severity": "critical", "category": "security"}]
        result = gate.evaluate(findings)
        assert result["counts"]["total"] == 1

    # ── print_report() ───────────────────────────────────────────────────

    def test_print_report_pass(self, caplog):
        import logging

        caplog.set_level(logging.INFO)
        gate = self.QualityGate(None)
        result = gate.evaluate([])
        gate.print_report(result)
        assert "PASSED" in caplog.text
        assert "Total" in caplog.text

    def test_print_report_fail(self, caplog):
        import logging

        caplog.set_level(logging.INFO)
        gate = self.QualityGate({"quality_gate": {"max_high": 0}})
        findings = [{"canonical_severity": "high", "category": "security"}]
        result = gate.evaluate(findings)
        gate.print_report(result)
        assert "FAILED" in caplog.text
        assert "❌" in caplog.text

    def test_print_report_all_checks_shown(self, caplog):
        import logging

        caplog.set_level(logging.INFO)
        gate = self.QualityGate(None)
        result = gate.evaluate([])
        gate.print_report(result)
        assert "High Severity" in caplog.text
        assert "Medium Severity" in caplog.text
        assert "Total Findings" in caplog.text
        assert "Security Findings" in caplog.text


# ═════════════════════════════════════════════════════════════════════════════
# SeverityScorer — Full Coverage
# ═════════════════════════════════════════════════════════════════════════════
class TestSeverityScorerFullCoverage:
    """Target: push severity_scorer.py from 34% → 85%+"""

    def setup_method(self):
        from CORE.engines.severity_scorer import SeverityScorer

        self.scorer = SeverityScorer()

    # ── RULE_SEVERITY table ───────────────────────────────────────────────

    def test_critical_mapped_rule(self):
        """SECURITY-047 is the only 'critical' rule, returned as-is."""
        result = self.scorer.score("SECURITY-047", {})
        assert result == "critical"

    def test_all_new_semgrep_custom_high_rules(self):
        for rule in [
            "CUSTOM-hardcoded-password",
            "CUSTOM-shell-injection",
            "CUSTOM-sql-injection",
            "CUSTOM-dangerous-eval-usage",
            "CUSTOM-command-injection",
        ]:
            assert self.scorer.score(rule, {}) == "high", f"{rule} should be high"

    def test_custom_medium_rules(self):
        for rule in ["CUSTOM-unsafe-pickle", "CUSTOM-bare-except"]:
            assert self.scorer.score(rule, {}) in ("medium", "high")

    def test_custom_low_rules(self):
        for rule in [
            "CUSTOM-open-without-context-manager",
            "CUSTOM-assert-for-validation",
            "CUSTOM-print-in-production",
            "CUSTOM-too-many-parameters",
            "CUSTOM-global-variable",
        ]:
            assert self.scorer.score(rule, {}) == "low", f"{rule} should be low"

    # ── CUSTOM-* keyword inference (_infer_custom_severity) ──────────────

    def test_custom_high_injection_keyword(self):
        assert self.scorer.score("CUSTOM-sql-injection-risk", {}) == "high"

    def test_custom_high_password_keyword(self):
        assert self.scorer.score("CUSTOM-password-exposure", {}) == "high"

    def test_custom_high_secret_keyword(self):
        assert self.scorer.score("CUSTOM-secret-leak", {}) == "high"

    def test_custom_high_eval_keyword(self):
        assert self.scorer.score("CUSTOM-unsafe-eval-call", {}) == "high"

    def test_custom_high_exec_keyword(self):
        assert self.scorer.score("CUSTOM-exec-injection", {}) == "high"

    def test_custom_high_xss_keyword(self):
        assert self.scorer.score("CUSTOM-reflected-xss", {}) == "high"

    def test_custom_high_command_keyword(self):
        assert self.scorer.score("CUSTOM-os-command-injection", {}) == "high"

    def test_custom_medium_pickle_keyword(self):
        assert self.scorer.score("CUSTOM-pickle-deserialize", {}) == "medium"

    def test_custom_medium_yaml_keyword(self):
        assert self.scorer.score("CUSTOM-yaml-unsafe-load", {}) == "medium"

    def test_custom_medium_ssl_keyword(self):
        assert self.scorer.score("CUSTOM-ssl-no-verify", {}) == "medium"

    def test_custom_medium_crypto_keyword(self):
        assert self.scorer.score("CUSTOM-weak-crypto-key", {}) == "medium"

    def test_custom_medium_except_keyword(self):
        assert self.scorer.score("CUSTOM-bare-except-clause", {}) == "medium"

    def test_custom_low_no_matching_keyword(self):
        assert self.scorer.score("CUSTOM-unused-variable", {}) == "low"

    def test_custom_low_unknown_pattern(self):
        assert self.scorer.score("CUSTOM-xyz-abc-123", {}) == "low"

    # ── Unmapped SECURITY-xxx → medium ───────────────────────────────────

    def test_unmapped_security_rule_defaults_medium(self):
        assert self.scorer.score("SECURITY-999", {}) == "medium"

    def test_unmapped_security_100_is_medium(self):
        assert self.scorer.score("SECURITY-100", {}) == "medium"

    # ── Unknown non-security rule → low ──────────────────────────────────

    def test_unmapped_unknown_rule_is_low(self):
        assert self.scorer.score("TOTALLY-UNKNOWN-999", {}) == "low"

    def test_unmapped_design_rule_is_low(self):
        assert self.scorer.score("DESIGN-999", {}) == "low"

    # ── COMPLEXITY-001 context adjustments ───────────────────────────────

    def test_complexity_zero_is_low(self):
        finding = {"tool_raw": {"original_output": {"complexity": 0}}}
        assert self.scorer.score("COMPLEXITY-001", finding) == "low"

    def test_complexity_exactly_medium_threshold_is_low(self):
        finding = {"tool_raw": {"original_output": {"complexity": 10}}}
        assert self.scorer.score("COMPLEXITY-001", finding) == "low"

    def test_complexity_11_is_medium(self):
        finding = {"tool_raw": {"original_output": {"complexity": 11}}}
        assert self.scorer.score("COMPLEXITY-001", finding) == "medium"

    def test_complexity_20_is_medium(self):
        finding = {"tool_raw": {"original_output": {"complexity": 20}}}
        assert self.scorer.score("COMPLEXITY-001", finding) == "medium"

    def test_complexity_21_is_high(self):
        finding = {"tool_raw": {"original_output": {"complexity": 21}}}
        assert self.scorer.score("COMPLEXITY-001", finding) == "high"

    def test_complexity_none_tool_raw_is_low(self):
        """No tool_raw at all → complexity defaults to 0 → low."""
        assert self.scorer.score("COMPLEXITY-001", {}) == "low"

    def test_complexity_from_message_high(self):
        # tool_raw=None triggers the except branch → message parsing runs
        finding = {"tool_raw": None, "message": "function has a complexity of 25."}
        assert self.scorer.score("COMPLEXITY-001", finding) == "high"

    def test_complexity_from_message_medium(self):
        finding = {"tool_raw": None, "message": "function has a complexity of 15."}
        assert self.scorer.score("COMPLEXITY-001", finding) == "medium"

    def test_complexity_from_message_low(self):
        finding = {"tool_raw": None, "message": "function has a complexity of 5."}
        assert self.scorer.score("COMPLEXITY-001", finding) == "low"

    # ── DEAD-001 context adjustments ────────────────────────────────────

    def test_dead_unused_class_is_medium(self):
        assert self.scorer.score("DEAD-001", {"message": "unused class Foo"}) == "medium"

    def test_dead_large_function_is_medium(self):
        finding = {
            "message": "unused function long_helper",
            "evidence": {"snippet": "x" * 150},
        }
        assert self.scorer.score("DEAD-001", finding) == "medium"

    def test_dead_small_function_is_low(self):
        finding = {
            "message": "unused function tiny",
            "evidence": {"snippet": "x" * 50},
        }
        assert self.scorer.score("DEAD-001", finding) == "low"

    def test_dead_unused_variable_is_low(self):
        assert self.scorer.score("DEAD-001", {"message": "unused variable x"}) == "low"

    def test_dead_no_message_is_low(self):
        assert self.scorer.score("DEAD-001", {}) == "low"

    # ── DUP-001 context adjustments ─────────────────────────────────────

    def test_dup_massive_tokens_via_tool_raw_is_high(self):
        finding = {"tool_raw": {"original_output": {"tokens": 201}}}
        assert self.scorer.score("DUP-001", finding) == "high"

    def test_dup_large_tokens_via_tool_raw_is_medium(self):
        finding = {"tool_raw": {"original_output": {"tokens": 150}}}
        assert self.scorer.score("DUP-001", finding) == "medium"

    def test_dup_small_tokens_uses_base_medium(self):
        finding = {"tool_raw": {"original_output": {"tokens": 50}}}
        assert self.scorer.score("DUP-001", finding) == "medium"

    def test_dup_from_message_high(self):
        # tool_raw=None triggers the except branch → message parsing runs
        finding = {"tool_raw": None, "message": "250 tokens cloned across files"}
        assert self.scorer.score("DUP-001", finding) == "high"

    def test_dup_from_message_medium(self):
        finding = {"tool_raw": None, "message": "150 tokens cloned"}
        assert self.scorer.score("DUP-001", finding) == "medium"

    def test_dup_no_tokens_uses_base(self):
        assert self.scorer.score("DUP-001", {}) == "medium"

    # ── get_severity_priority() ─────────────────────────────────────────

    def test_priority_high_is_1(self):
        assert self.scorer.get_severity_priority("high") == 1

    def test_priority_medium_is_2(self):
        assert self.scorer.get_severity_priority("medium") == 2

    def test_priority_low_is_3(self):
        assert self.scorer.get_severity_priority("low") == 3

    def test_priority_unknown_is_99(self):
        assert self.scorer.get_severity_priority("unknown") == 99

    # ── score_severity() convenience function ────────────────────────────

    def test_score_severity_convenience_function(self):
        from CORE.engines.severity_scorer import score_severity

        assert score_severity("SECURITY-001", {}) == "high"
        assert score_severity("IMPORT-001", {}) == "low"
        assert score_severity("SOLID-001", {}) == "medium"

    def test_score_severity_unknown_rule(self):
        from CORE.engines.severity_scorer import score_severity

        assert score_severity("TOTALLY-CUSTOM-XYZ", {}) == "low"

    # ── Extract helper edge cases ────────────────────────────────────────

    def test_extract_complexity_bad_message_returns_0(self):
        """Message with 'complexity of' but unparseable value."""
        finding = {"message": "complexity of notanumber"}
        # Should not crash, returns 0 → low
        result = self.scorer.score("COMPLEXITY-001", finding)
        assert result == "low"

    def test_extract_duplication_size_bad_message(self):
        """Message with 'tokens' but unparseable → falls back to base."""
        finding = {"message": "many tokens in code"}
        # Should not crash
        result = self.scorer.score("DUP-001", finding)
        assert result in ("high", "medium", "low")
