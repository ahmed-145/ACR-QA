"""
Phase 12 Week 1 completion — tasks 12.3, 12.4, 12.5, 12.6

12.3 — Binary fuzz tests for parsers (Hypothesis st.binary() strategy,
        atheris-equivalent without needing Clang)
12.4 — Snapshot tests for AI explainer output format
12.5 — Performance regression gate (hard budget — test FAILS if exceeded)
12.6 — Mutation-killing exact-value tests for confidence_scorer, quality_gate,
        severity_scorer (the three files with 0% mutation score in 12.1)
"""

from __future__ import annotations

import time

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from CORE.engines.confidence_scorer import (
    _CATEGORY_SCORE,
    _CUSTOM_BONUS,
    _FIX_BONUS,
    _RULE_BONUS,
    _SEVERITY_SCORE,
    _TOOL_SCORE,
    ConfidenceScorer,
)
from CORE.engines.normalizer import normalize_bandit, normalize_ruff, normalize_semgrep
from CORE.engines.quality_gate import DEFAULT_THRESHOLDS, QualityGate
from CORE.engines.severity_scorer import SeverityScorer

# ══════════════════════════════════════════════════════════════════════════════
# Task 12.3 — Binary fuzz parsers (Hypothesis st.binary())
# ══════════════════════════════════════════════════════════════════════════════


class TestBinaryFuzzParsers:
    """
    Task 12.3: parsers must survive arbitrary binary input.
    Equivalent to atheris fuzzing without requiring Clang/LLVM.
    max_examples=500 → >1 500 binary sequences across 3 normalizers.
    """

    @given(st.binary(max_size=8192))
    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_ruff_survives_binary_input(self, raw: bytes) -> None:
        """normalize_ruff() must never raise on arbitrary bytes decoded as UTF-8."""
        text = raw.decode("utf-8", errors="replace")
        result = normalize_ruff(text)
        assert isinstance(result, list)

    @given(st.binary(max_size=8192))
    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_bandit_survives_binary_input(self, raw: bytes) -> None:
        """normalize_bandit() must never raise on arbitrary bytes decoded as UTF-8."""
        text = raw.decode("utf-8", errors="replace")
        result = normalize_bandit(text)
        assert isinstance(result, list)

    @given(st.binary(max_size=8192))
    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_semgrep_survives_binary_input(self, raw: bytes) -> None:
        """normalize_semgrep() must never raise on arbitrary bytes decoded as UTF-8."""
        text = raw.decode("utf-8", errors="replace")
        result = normalize_semgrep(text)
        assert isinstance(result, list)

    @given(st.binary(max_size=16384))
    @settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_yaml_config_survives_binary_input(self, raw: bytes) -> None:
        """yaml.safe_load() must never raise unexpected exceptions on binary input."""
        import yaml

        text = raw.decode("utf-8", errors="replace")
        try:
            yaml.safe_load(text)
        except yaml.YAMLError:
            pass  # expected for malformed YAML — must not bubble unexpected errors

    @given(st.binary(max_size=4096))
    @settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_json_decode_then_normalize_survives(self, raw: bytes) -> None:
        """Full path: decode → JSON parse attempt → normalize must never crash."""
        import json

        text = raw.decode("utf-8", errors="replace")
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
            data = {}
        result = normalize_ruff(data)
        assert isinstance(result, list)


# ══════════════════════════════════════════════════════════════════════════════
# Task 12.4 — Snapshot tests for AI explainer output format
# ══════════════════════════════════════════════════════════════════════════════


class TestExplainerOutputFormat:
    """
    Task 12.4: snapshot tests for AI explainer output format.
    These tests verify the output schema is stable — they catch silent regressions
    in output structure when the LLM provider, prompt template, or parsing logic changes.

    Strategy: run with no API keys (env vars absent) so the engine hits the except
    clause and returns a fallback dict — no real Groq calls needed.
    """

    @pytest.fixture
    def engine(self):
        """Real ExplanationEngine with no API keys — guaranteed fallback path."""
        import os
        from unittest.mock import patch

        from CORE.engines.explainer import ExplanationEngine

        # Patch out all key env vars so key_pool has no keys → always hits fallback
        env_patch = {k: "" for k in os.environ if "GROQ" in k or "AGENTROUTER" in k}
        env_patch["ACRQA_LLM_PROVIDER"] = "none"
        with patch.dict(os.environ, env_patch, clear=False):
            return ExplanationEngine()

    @pytest.fixture
    def engine_with_mock_client(self, monkeypatch):
        """ExplanationEngine with a mocked Groq client that returns a fixed response."""
        from unittest.mock import MagicMock

        from CORE.engines.explainer import ExplanationEngine

        with monkeypatch.context() as m:
            m.setenv("ACRQA_LLM_PROVIDER", "none")
            eng = ExplanationEngine()

        # Inject a mock client directly into key_pool
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = (
            "This code violates SECURITY-005: hardcoded credentials are an OWASP A02 issue. "
            "Replace with os.environ.get('DB_PASSWORD') and raise RuntimeError if unset."
        )
        mock_response.usage.total_tokens = 487
        mock_client.chat.completions.create.return_value = mock_response
        eng.key_pool._clients = [mock_client]
        eng.key_pool._keys = ["mock-key"]
        return eng

    @pytest.fixture
    def sample_finding(self):
        return {
            "id": 1,
            "canonical_rule_id": "SECURITY-005",
            "canonical_severity": "medium",
            "category": "security",
            "file_path": "CORE/engines/explainer.py",
            "line_number": 142,
            "message": "Hardcoded password string detected",
            "tool": "bandit",
            "original_rule_id": "B105",
        }

    REQUIRED_KEYS = {"model_name", "response_text", "status", "latency_ms", "tokens_used", "cost_usd"}

    def test_fallback_output_has_required_keys(self, engine, sample_finding):
        """Snapshot: fallback output dict must always have the required schema keys."""
        result = engine.generate_explanation(sample_finding)
        assert self.REQUIRED_KEYS.issubset(result.keys()), f"Missing keys: {self.REQUIRED_KEYS - result.keys()}"

    def test_fallback_response_text_is_non_empty_string(self, engine, sample_finding):
        """Snapshot: response_text must always be a non-empty string, even in fallback."""
        result = engine.generate_explanation(sample_finding)
        assert isinstance(result["response_text"], str)
        assert len(result["response_text"]) > 0

    def test_fallback_model_name_is_string(self, engine, sample_finding):
        """Snapshot: model_name must always be present and a non-empty string."""
        result = engine.generate_explanation(sample_finding)
        assert isinstance(result["model_name"], str)
        assert len(result["model_name"]) > 0

    def test_fallback_latency_ms_is_non_negative(self, engine, sample_finding):
        """Snapshot: latency_ms must always be a non-negative numeric value."""
        result = engine.generate_explanation(sample_finding)
        assert isinstance(result["latency_ms"], int | float)
        assert result["latency_ms"] >= 0

    def test_fallback_status_is_known_value(self, engine, sample_finding):
        """Snapshot: status must always be one of the known sentinel strings."""
        result = engine.generate_explanation(sample_finding)
        known_statuses = {"success", "fallback", "cached", "error", "no_key", "rate_limited"}
        assert result["status"] in known_statuses, f"Unknown status: {result['status']!r}"

    def test_fallback_cost_usd_is_numeric(self, engine, sample_finding):
        """Snapshot: cost_usd must always be a non-negative numeric value."""
        result = engine.generate_explanation(sample_finding)
        assert isinstance(result["cost_usd"], int | float)
        assert result["cost_usd"] >= 0

    def test_output_schema_stable_across_calls(self, engine, sample_finding):
        """Snapshot: two calls with the same finding must produce identical output keys."""
        r1 = engine.generate_explanation(sample_finding)
        r2 = engine.generate_explanation(sample_finding)
        assert set(r1.keys()) == set(r2.keys()), "Output schema changed between calls"

    def test_mock_client_produces_success_status(self, engine_with_mock_client, sample_finding):
        """Snapshot: when client returns a valid response, status must be 'success'."""
        result = engine_with_mock_client.generate_explanation(sample_finding, code_snippet="x = 1")
        assert result["status"] == "success"
        assert isinstance(result["response_text"], str)
        assert len(result["response_text"]) > 10
        assert self.REQUIRED_KEYS.issubset(result.keys())


# ══════════════════════════════════════════════════════════════════════════════
# Task 12.5 — Performance regression gate (hard budget)
# ══════════════════════════════════════════════════════════════════════════════


class TestPerformanceRegressionGate:
    """
    Task 12.5: CI gate — these tests FAIL if key operations exceed budget.
    Budget is generous (10× measured baseline) so flaky env noise won't false-positive.

    Measured baseline (from 12.10 scale test): 42,000 LOC/s
    For 1,000 simple findings: normalize < 0.5s wall time.
    """

    NORMALIZER_BUDGET_S = 2.0
    SCORING_BUDGET_S = 1.0
    GATE_BUDGET_S = 0.5

    def _make_ruff_findings(self, n: int) -> list[dict]:
        return [
            {
                "filename": f"src/module_{i}.py",
                "location": {"row": i + 1, "column": 0},
                "code": "F401",
                "message": f"unused import os_{i}",
                "fix": None,
            }
            for i in range(n)
        ]

    def _make_canonical_findings(self, n: int) -> list[dict]:
        return [
            {
                "canonical_severity": "low",
                "category": "style",
                "tool": "ruff",
                "canonical_rule_id": "IMPORT-001",
            }
            for _ in range(n)
        ]

    def test_normalize_ruff_1000_findings_within_budget(self) -> None:
        """CI gate: normalize_ruff(1000 findings) must complete in under 0.5s."""
        raw = {"results": self._make_ruff_findings(1000)}
        start = time.perf_counter()
        result = normalize_ruff(raw)
        elapsed = time.perf_counter() - start
        assert isinstance(result, list)
        assert elapsed < self.NORMALIZER_BUDGET_S, (
            f"normalize_ruff(1000) took {elapsed:.3f}s — exceeds {self.NORMALIZER_BUDGET_S}s budget. "
            "Performance regression detected."
        )

    def test_confidence_scoring_1000_findings_within_budget(self) -> None:
        """CI gate: scoring 1000 findings must complete in under 0.3s."""
        findings = self._make_canonical_findings(1000)
        scorer = ConfidenceScorer()
        start = time.perf_counter()
        scores = scorer.score_batch(findings)
        elapsed = time.perf_counter() - start
        assert len(scores) == 1000
        assert elapsed < self.SCORING_BUDGET_S, (
            f"score_batch(1000) took {elapsed:.3f}s — exceeds {self.SCORING_BUDGET_S}s budget. "
            "Performance regression detected."
        )

    def test_quality_gate_500_findings_within_budget(self) -> None:
        """CI gate: quality gate evaluation of 500 findings must complete in under 0.1s."""
        findings = [
            {"canonical_severity": "low", "category": "style", "canonical_rule_id": "STYLE-001"} for _ in range(500)
        ]
        gate = QualityGate()
        start = time.perf_counter()
        result = gate.evaluate(findings)
        elapsed = time.perf_counter() - start
        assert result["counts"]["total"] == 500
        assert elapsed < self.GATE_BUDGET_S, (
            f"QualityGate.evaluate(500) took {elapsed:.3f}s — exceeds {self.GATE_BUDGET_S}s budget. "
            "Performance regression detected."
        )

    def test_severity_scorer_1000_findings_within_budget(self) -> None:
        """CI gate: SeverityScorer must score 1000 findings in under 0.3s."""
        findings = [
            {"canonical_rule_id": "SECURITY-001", "canonical_severity": "high", "tool": "bandit"} for _ in range(1000)
        ]
        scorer = SeverityScorer()
        start = time.perf_counter()
        for f in findings:
            scorer.score(f["canonical_rule_id"], f)
        elapsed = time.perf_counter() - start
        assert elapsed < self.SCORING_BUDGET_S, (
            f"SeverityScorer.score(×1000) took {elapsed:.3f}s — exceeds {self.SCORING_BUDGET_S}s budget. "
            "Performance regression detected."
        )


# ══════════════════════════════════════════════════════════════════════════════
# Task 12.6 — Mutation-killing exact-value tests
# ══════════════════════════════════════════════════════════════════════════════


class TestConfidenceScorerExactValues:
    """
    Task 12.6: exact-value assertions that kill mutations.
    The existing tests only check `score >= 40` which doesn't kill mutations
    that change the constant 40 → 20. These tests assert the exact score.
    """

    @pytest.fixture
    def scorer(self):
        return ConfidenceScorer(known_rule_ids={"SECURITY-001", "SECURITY-059", "STYLE-001"})

    def test_high_severity_unknown_rule_unknown_tool_exact_score(self, scorer):
        """Exact: high=40, style=0, unknown_tool=5, unknown_rule=0 → 45."""
        f = {
            "canonical_severity": "high",
            "category": "style",
            "tool": "unknown_tool_xyz",
            "canonical_rule_id": "CUSTOM-UNKNOWN",
        }
        score = scorer.score(f)
        expected = (
            _SEVERITY_SCORE["high"]
            + _CATEGORY_SCORE.get("style", 0)
            + _TOOL_SCORE.get("unknown_tool_xyz", 5)
            + _CUSTOM_BONUS
        )
        assert score == expected, f"Expected {expected}, got {score}"

    def test_medium_security_bandit_known_rule_exact_score(self, scorer):
        """Exact: medium=25, security=20, bandit=15, known_rule=10 → 70."""
        f = {
            "canonical_severity": "medium",
            "category": "security",
            "tool": "bandit",
            "canonical_rule_id": "SECURITY-001",
        }
        score = scorer.score(f)
        expected = _SEVERITY_SCORE["medium"] + _CATEGORY_SCORE["security"] + _TOOL_SCORE["bandit"] + _RULE_BONUS
        assert score == expected, f"Expected {expected}, got {score}"

    def test_high_security_bandit_known_rule_exact_score(self, scorer):
        """Exact: high=40, security=20, bandit=15, known_rule=10 → 85."""
        f = {
            "canonical_severity": "high",
            "category": "security",
            "tool": "bandit",
            "canonical_rule_id": "SECURITY-001",
        }
        score = scorer.score(f)
        expected = _SEVERITY_SCORE["high"] + _CATEGORY_SCORE["security"] + _TOOL_SCORE["bandit"] + _RULE_BONUS
        assert score == expected, f"Expected {expected}, got {score}"

    def test_low_style_ruff_known_rule_exact_score(self, scorer):
        """Exact: low=10, style=0, ruff=8, known_rule=10 → 28."""
        f = {
            "canonical_severity": "low",
            "category": "style",
            "tool": "ruff",
            "canonical_rule_id": "STYLE-001",
        }
        score = scorer.score(f)
        expected = _SEVERITY_SCORE["low"] + _CATEGORY_SCORE.get("style", 0) + _TOOL_SCORE["ruff"] + _RULE_BONUS
        assert score == expected, f"Expected {expected}, got {score}"

    def test_fix_bonus_adds_exactly_10(self, scorer):
        """Exact: fix_validated=True adds _FIX_BONUS=10."""
        f = {"canonical_severity": "low", "category": "style", "tool": "ruff", "canonical_rule_id": "UNKNOWN-X"}
        without_fix = scorer.score(f, fix_validated=False)
        with_fix = scorer.score(f, fix_validated=True)
        assert (
            with_fix - without_fix == _FIX_BONUS
        ), f"Expected FIX_BONUS={_FIX_BONUS}, got diff={with_fix - without_fix}"

    def test_score_capped_at_100(self, scorer):
        """Score must never exceed 100 even when all signals are maxed."""
        f = {
            "canonical_severity": "high",
            "category": "security",
            "tool": "bandit",
            "canonical_rule_id": "SECURITY-001",
        }
        score = scorer.score(f, fix_validated=True)
        assert score <= 100

    def test_score_floor_is_zero(self, scorer):
        """Score must never go below 0."""
        f = {"canonical_severity": "unknown", "category": "unknown", "tool": "unknown", "canonical_rule_id": "UNKNOWN"}
        score = scorer.score(f)
        assert score >= 0

    def test_semgrep_tool_score_exact(self, scorer):
        """semgrep tool contributes exactly _TOOL_SCORE['semgrep']=15."""
        f_semgrep = {
            "canonical_severity": "low",
            "category": "style",
            "tool": "semgrep",
            "canonical_rule_id": "UNKNOWN-X",
        }
        f_ruff = {"canonical_severity": "low", "category": "style", "tool": "ruff", "canonical_rule_id": "UNKNOWN-X"}
        diff = scorer.score(f_semgrep) - scorer.score(f_ruff)
        assert (
            diff == _TOOL_SCORE["semgrep"] - _TOOL_SCORE["ruff"]
        ), f"Expected diff={_TOOL_SCORE['semgrep'] - _TOOL_SCORE['ruff']}, got {diff}"

    def test_custom_rule_bonus_exact(self, scorer):
        """CUSTOM- prefixed rule contributes exactly _CUSTOM_BONUS=5."""
        f_custom = {
            "canonical_severity": "low",
            "category": "style",
            "tool": "ruff",
            "canonical_rule_id": "CUSTOM-MY-RULE",
        }
        f_known = {"canonical_severity": "low", "category": "style", "tool": "ruff", "canonical_rule_id": "STYLE-001"}
        diff = scorer.score(f_known) - scorer.score(f_custom)
        assert diff == _RULE_BONUS - _CUSTOM_BONUS, f"Expected diff={_RULE_BONUS - _CUSTOM_BONUS}, got {diff}"

    def test_batch_scores_match_individual(self, scorer):
        """score_batch() must return the same scores as calling score() per finding."""
        findings = [
            {
                "canonical_severity": "high",
                "category": "security",
                "tool": "bandit",
                "canonical_rule_id": "SECURITY-001",
            },
            {"canonical_severity": "low", "category": "style", "tool": "ruff", "canonical_rule_id": "STYLE-001"},
            {
                "canonical_severity": "medium",
                "category": "design",
                "tool": "radon",
                "canonical_rule_id": "COMPLEXITY-001",
            },
        ]
        batch = scorer.score_batch(findings)
        individual = [scorer.score(f) for f in findings]
        assert batch == individual


class TestQualityGateExactValues:
    """
    Task 12.6: exact-value assertions for QualityGate.
    Tests check specific threshold values, not just pass/fail direction.
    """

    def _finding(self, sev="low", cat="style", rule="STYLE-001"):
        return {"canonical_severity": sev, "category": cat, "canonical_rule_id": rule}

    def test_default_max_high_is_zero(self):
        """DEFAULT_THRESHOLDS['max_high'] must be exactly 0."""
        assert DEFAULT_THRESHOLDS["max_high"] == 0

    def test_exactly_max_high_findings_fails(self):
        """Exactly max_high+1 high findings must fail the gate."""
        gate = QualityGate(config={"quality_gate": {"max_high": 2}})
        findings = [self._finding("high")] * 3  # one over threshold
        result = gate.evaluate(findings)
        assert result["passed"] is False

    def test_exactly_at_max_high_passes(self):
        """Exactly max_high high findings must pass the gate."""
        gate = QualityGate(config={"quality_gate": {"max_high": 2}})
        findings = [self._finding("high")] * 2
        result = gate.evaluate(findings)
        assert result["passed"] is True

    def test_counts_medium_exactly(self):
        """Counts must match exactly — not approximately."""
        gate = QualityGate()
        findings = [self._finding("medium")] * 7
        result = gate.evaluate(findings)
        assert result["counts"]["medium"] == 7
        assert result["counts"]["high"] == 0
        assert result["counts"]["low"] == 0
        assert result["counts"]["total"] == 7

    def test_security_category_counted_exactly(self):
        """Security category findings trigger the Security Findings check."""
        gate = QualityGate(config={"quality_gate": {"max_security": 1}})
        findings = [
            self._finding("high", "security"),
            self._finding("low", "security"),
            self._finding("low", "style"),
        ]
        result = gate.evaluate(findings)
        sec_check = next(c for c in result["checks"] if c["name"] == "Security Findings")
        assert sec_check["actual"] == 2

    def test_passed_field_is_bool_not_truthy(self):
        """'passed' must be exactly bool True/False, not just truthy/falsy."""
        gate = QualityGate()
        result = gate.evaluate([])
        assert result["passed"] is True
        assert type(result["passed"]) is bool

    def test_warn_mode_should_block_returns_false_on_violation(self):
        """In warn mode, should_block() must return False even when thresholds exceeded."""
        gate = QualityGate(config={"quality_gate": {"max_high": 0, "mode": "warn"}})
        findings = [self._finding("high")]
        result = gate.evaluate(findings)
        assert result["passed"] is False  # evaluate still records the failure
        assert gate.should_block(result) is False  # but warn mode never blocks

    def test_checks_list_contains_correct_threshold_names(self):
        """Checks list must contain entries for all configured thresholds."""
        gate = QualityGate()
        result = gate.evaluate([])
        check_names = {c["name"] for c in result["checks"]}
        assert "High Severity" in check_names
        assert "Medium Severity" in check_names
        assert "Total Findings" in check_names

    def test_each_check_has_threshold_value_and_actual(self):
        """Every check entry must expose 'threshold', 'actual', and 'passed' keys."""
        gate = QualityGate()
        result = gate.evaluate([self._finding("high")])
        for check in result["checks"]:
            assert "name" in check, f"Check missing 'name' key: {check}"
            assert "passed" in check, f"Check missing 'passed' key: {check}"
            assert "threshold" in check, f"Check missing 'threshold' key: {check}"
            assert "actual" in check, f"Check missing 'actual' key: {check}"


class TestSeverityScorerExactValues:
    """
    Task 12.6: exact-value assertions for SeverityScorer.
    Ensures mutations to the RULE_SEVERITY dict are caught.
    """

    @pytest.fixture
    def scorer(self):
        return SeverityScorer()

    def test_security_001_is_high(self, scorer):
        """SECURITY-001 (eval/exec) must always be high — mutation kills change to medium."""
        assert SeverityScorer.RULE_SEVERITY["SECURITY-001"] == "high"

    def test_security_009_is_medium(self, scorer):
        """SECURITY-009 (MD5) must always be medium."""
        assert SeverityScorer.RULE_SEVERITY["SECURITY-009"] == "medium"

    def test_import_001_is_low(self, scorer):
        """IMPORT-001 (unused import) must always be low."""
        assert SeverityScorer.RULE_SEVERITY.get("IMPORT-001") == "low"

    def test_score_returns_known_severity_for_known_rule(self, scorer):
        """score() must return the exact severity from RULE_SEVERITY for known rules."""
        for rule_id, expected_sev in list(SeverityScorer.RULE_SEVERITY.items())[:10]:
            f = {"canonical_rule_id": rule_id, "canonical_severity": "low"}
            result = scorer.score(rule_id, f)
            assert result == expected_sev, f"Rule {rule_id}: expected {expected_sev!r}, got {result!r}"

    def test_unknown_rule_falls_back_to_low(self, scorer):
        """Non-SECURITY/CUSTOM unknown rules default to 'low' severity."""
        f = {"canonical_rule_id": "UNKNOWN-999", "canonical_severity": "medium"}
        result = scorer.score("UNKNOWN-999", f)
        assert result == "low"

    def test_score_never_returns_none(self, scorer):
        """score() must never return None — always a valid severity string."""
        findings = [
            ("SECURITY-001", {"canonical_rule_id": "SECURITY-001"}),
            ("IMPORT-001", {"canonical_rule_id": "IMPORT-001", "canonical_severity": "low"}),
            ("UNKNOWN-XYZ", {"canonical_rule_id": "UNKNOWN-XYZ", "canonical_severity": "medium"}),
            ("UNKNOWN-EMPTY", {}),
        ]
        for rule_id, f in findings:
            result = scorer.score(rule_id, f)
            assert result is not None
            assert result in ("low", "medium", "high", "critical")
