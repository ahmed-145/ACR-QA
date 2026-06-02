"""
Tests for CORE/engines/confirmed_tier.py — the Confirmed Tier engine.
"""

from __future__ import annotations

import pytest

from CORE.engines.confirmed_tier import CONFIRMED_RULE_SET, ConfirmedTierEngine

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_finding(**overrides) -> dict:
    base = {
        "canonical_severity": "high",
        "canonical_rule_id": "SECURITY-001",
        "file": "src/app.py",
        "tool_raw": {"tool_name": "semgrep"},
    }
    base.update(overrides)
    return base


def _bandit_finding(**overrides) -> dict:
    base = {
        "canonical_severity": "high",
        "canonical_rule_id": "SECURITY-001",
        "file": "src/app.py",
        "tool_raw": {
            "tool_name": "bandit",
            "original_output": {"issue_confidence": "HIGH"},
        },
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Rule set sanity
# ---------------------------------------------------------------------------


class TestRuleSet:
    def test_non_empty(self):
        assert len(CONFIRMED_RULE_SET) >= 20

    def test_contains_known_rules(self):
        for r in ("SECURITY-001", "SECURITY-021", "SECRET-001", "SQLI-001"):
            assert r in CONFIRMED_RULE_SET

    def test_is_frozenset(self):
        assert isinstance(CONFIRMED_RULE_SET, frozenset)


# ---------------------------------------------------------------------------
# Base gate logic
# ---------------------------------------------------------------------------


class TestBaseGates:
    def setup_method(self):
        self.engine = ConfirmedTierEngine()

    def test_passes_all_gates(self):
        f = _make_finding()
        r = self.engine.classify(f)
        assert r.in_confirmed_tier is True

    def test_fails_low_severity(self):
        f = _make_finding(canonical_severity="low")
        r = self.engine.classify(f)
        assert r.in_confirmed_tier is False
        assert any("severity" in reason for reason in r.reasons)

    def test_fails_medium_severity(self):
        f = _make_finding(canonical_severity="medium")
        assert self.engine.classify(f).in_confirmed_tier is False

    def test_fails_unknown_rule(self):
        f = _make_finding(canonical_rule_id="CUSTOM-999")
        r = self.engine.classify(f)
        assert r.in_confirmed_tier is False
        assert any("CUSTOM-999" in reason for reason in r.reasons)

    def test_fails_test_file_path(self):
        for path in [
            "tests/test_app.py",
            "TESTS/test_something.py",
            "src/conftest.py",
            "examples/demo.py",
            "migrations/001_init.py",
        ]:
            f = _make_finding(file=path)
            result = self.engine.classify(f)
            assert result.in_confirmed_tier is False, f"Expected fail for {path}"

    def test_passes_production_path(self):
        for path in ["src/app.py", "api/views.py", "CORE/main.py", "server/handlers.go"]:
            f = _make_finding(file=path)
            result = self.engine.classify(f)
            assert result.in_confirmed_tier is True, f"Expected pass for {path}"

    def test_bandit_high_confidence_passes(self):
        f = _bandit_finding()
        assert self.engine.classify(f).in_confirmed_tier is True

    def test_bandit_medium_confidence_fails(self):
        f = _bandit_finding()
        f["tool_raw"]["original_output"]["issue_confidence"] = "MEDIUM"
        assert self.engine.classify(f).in_confirmed_tier is False

    def test_bandit_low_confidence_fails(self):
        f = _bandit_finding()
        f["tool_raw"]["original_output"]["issue_confidence"] = "LOW"
        assert self.engine.classify(f).in_confirmed_tier is False

    def test_non_bandit_skips_confidence_gate(self):
        # For non-Bandit tools, the confidence gate does not apply
        f = _make_finding(
            tool_raw={"tool_name": "semgrep"},
        )
        assert self.engine.classify(f).in_confirmed_tier is True


# ---------------------------------------------------------------------------
# Reachability signals
# ---------------------------------------------------------------------------


class TestReachabilitySignals:
    def setup_method(self):
        self.engine = ConfirmedTierEngine()

    def test_no_signal_returns_none(self):
        f = _make_finding()
        r = self.engine.classify(f)
        assert r.reachability_signal == "none"

    def test_exploit_verified_signal(self):
        f = _make_finding(exploit_tier="verified-exploitable")
        r = self.engine.classify(f)
        assert r.reachability_signal == "exploit"

    def test_taint_source_signal(self):
        f = _make_finding(tool_raw={"tool_name": "semgrep", "taint_source": "request.args"})
        r = self.engine.classify(f)
        assert r.reachability_signal == "taint"

    def test_call_graph_reachable_signal(self):
        f = _make_finding(reachability_status="REACHABLE")
        r = self.engine.classify(f)
        assert r.reachability_signal == "call_graph"

    def test_exploit_beats_taint(self):
        f = _make_finding(
            exploit_tier="verified-exploitable",
            reachability_status="REACHABLE",
            tool_raw={"tool_name": "semgrep", "taint_source": "x"},
        )
        r = self.engine.classify(f)
        assert r.reachability_signal == "exploit"

    def test_taint_beats_call_graph(self):
        f = _make_finding(
            reachability_status="REACHABLE",
            tool_raw={"tool_name": "semgrep", "taint_source": "x"},
        )
        r = self.engine.classify(f)
        assert r.reachability_signal == "taint"

    def test_unreachable_does_not_trigger_signal(self):
        f = _make_finding(reachability_status="UNREACHABLE")
        r = self.engine.classify(f)
        assert r.reachability_signal == "none"


# ---------------------------------------------------------------------------
# enrich_findings batch method
# ---------------------------------------------------------------------------


class TestEnrichFindings:
    def setup_method(self):
        self.engine = ConfirmedTierEngine()

    def test_adds_confirmed_tier_field(self):
        findings = [_make_finding(), _make_finding(canonical_severity="low")]
        out = self.engine.enrich_findings(findings)
        assert len(out) == 2
        assert out[0]["confirmed_tier"] is True
        assert out[1]["confirmed_tier"] is False

    def test_adds_signal_field(self):
        findings = [_make_finding()]
        out = self.engine.enrich_findings(findings)
        assert "confirmed_tier_signal" in out[0]

    def test_empty_list_ok(self):
        assert self.engine.enrich_findings([]) == []

    def test_does_not_mutate_original(self):
        f = _make_finding()
        original_keys = set(f.keys())
        self.engine.enrich_findings([f])
        assert set(f.keys()) == original_keys

    def test_handles_bad_finding_gracefully(self):
        bad = {"garbage": True}
        out = self.engine.enrich_findings([bad])
        assert out[0]["confirmed_tier"] is False
        assert out[0]["confirmed_tier_signal"] == "none"

    def test_counts_confirmed_correctly(self):
        findings = [
            _make_finding(),  # passes
            _make_finding(),  # passes
            _make_finding(canonical_severity="low"),  # fails
            _make_finding(canonical_rule_id="CUSTOM-X"),  # fails
        ]
        out = self.engine.enrich_findings(findings)
        confirmed = sum(1 for f in out if f.get("confirmed_tier"))
        assert confirmed == 2


# ---------------------------------------------------------------------------
# All confirmed rules survive round-trip classification
# ---------------------------------------------------------------------------


class TestAllConfirmedRulesPass:
    @pytest.mark.parametrize("rule", sorted(CONFIRMED_RULE_SET))
    def test_each_confirmed_rule_passes(self, rule):
        engine = ConfirmedTierEngine()
        f = _make_finding(canonical_rule_id=rule)
        assert engine.classify(f).in_confirmed_tier is True


# ---------------------------------------------------------------------------
# confirmed_rule_set() static accessor
# ---------------------------------------------------------------------------


def test_confirmed_rule_set_static_accessor():
    assert ConfirmedTierEngine.confirmed_rule_set() is CONFIRMED_RULE_SET
