"""
Tests for CORE/engines/path_feasibility.py — Feature 7 (LLM4PFA)
Target: 85%+ coverage. HTTP calls are fully mocked.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from CORE.engines.path_feasibility import (
    FEASIBILITY_PROMPT,
    PathFeasibilityResult,
    PathFeasibilityValidator,
    _parse_feasibility_response,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def validator():
    return PathFeasibilityValidator()


@pytest.fixture
def high_security_finding():
    return {
        "canonical_severity": "high",
        "category": "security",
        "canonical_rule_id": "SECURITY-001",
        "file_path": "app.py",
        "line_number": 42,
        "message": "SQL injection risk",
    }


@pytest.fixture
def low_style_finding():
    return {
        "canonical_severity": "low",
        "category": "style",
        "canonical_rule_id": "STYLE-001",
        "file_path": "utils.py",
        "line_number": 10,
        "message": "Unused variable",
    }


def _make_result(verdict="REACHABLE", confidence="HIGH", reasoning="Test reasoning"):
    return PathFeasibilityResult(
        verdict=verdict,
        confidence=confidence,
        reasoning=reasoning,
        latency_ms=100,
        rule_id="SECURITY-001",
        file_path="app.py",
        line_number=42,
    )


# ── PathFeasibilityResult ─────────────────────────────────────────────────────


class TestPathFeasibilityResult:
    def test_is_unreachable_true(self):
        r = _make_result(verdict="UNREACHABLE")
        assert r.is_unreachable is True

    def test_is_unreachable_false_for_reachable(self):
        r = _make_result(verdict="REACHABLE")
        assert r.is_unreachable is False

    def test_is_unreachable_false_for_unknown(self):
        r = _make_result(verdict="UNKNOWN")
        assert r.is_unreachable is False

    def test_confidence_penalty_unreachable_high(self):
        r = _make_result(verdict="UNREACHABLE", confidence="HIGH")
        assert r.confidence_penalty == 30

    def test_confidence_penalty_unreachable_medium(self):
        r = _make_result(verdict="UNREACHABLE", confidence="MEDIUM")
        assert r.confidence_penalty == 20

    def test_confidence_penalty_unreachable_low(self):
        r = _make_result(verdict="UNREACHABLE", confidence="LOW")
        assert r.confidence_penalty == 10

    def test_confidence_penalty_unreachable_unknown_confidence(self):
        r = _make_result(verdict="UNREACHABLE", confidence="BANANA")
        assert r.confidence_penalty == 15

    def test_confidence_penalty_unknown_verdict(self):
        r = _make_result(verdict="UNKNOWN")
        assert r.confidence_penalty == 5

    def test_confidence_penalty_reachable_is_zero(self):
        r = _make_result(verdict="REACHABLE")
        assert r.confidence_penalty == 0

    def test_to_dict_keys(self):
        r = _make_result(verdict="REACHABLE", confidence="HIGH", reasoning="looks fine")
        d = r.to_dict()
        assert "feasibility_verdict" in d
        assert "feasibility_confidence" in d
        assert "feasibility_reasoning" in d
        assert "feasibility_latency_ms" in d
        assert "feasibility_penalty" in d
        assert "is_unreachable" in d

    def test_to_dict_values(self):
        r = _make_result(verdict="UNREACHABLE", confidence="MEDIUM", reasoning="dead code")
        d = r.to_dict()
        assert d["feasibility_verdict"] == "UNREACHABLE"
        assert d["feasibility_confidence"] == "MEDIUM"
        assert d["feasibility_reasoning"] == "dead code"
        assert d["feasibility_penalty"] == 20
        assert d["is_unreachable"] is True


# ── _parse_feasibility_response ───────────────────────────────────────────────


class TestParseFeasibilityResponse:
    def test_parses_reachable(self):
        text = "VERDICT: REACHABLE\nCONFIDENCE: HIGH\nREASONING: User input flows to sink."
        v, c, r = _parse_feasibility_response(text)
        assert v == "REACHABLE"
        assert c == "HIGH"
        assert "User input" in r

    def test_parses_unreachable(self):
        text = "VERDICT: UNREACHABLE\nCONFIDENCE: MEDIUM\nREASONING: Guard clause prevents execution."
        v, c, r = _parse_feasibility_response(text)
        assert v == "UNREACHABLE"
        assert c == "MEDIUM"

    def test_parses_unknown(self):
        text = "VERDICT: UNKNOWN\nCONFIDENCE: LOW\nREASONING: Insufficient context."
        v, c, r = _parse_feasibility_response(text)
        assert v == "UNKNOWN"
        assert c == "LOW"

    def test_invalid_verdict_defaults_to_unknown(self):
        text = "VERDICT: MAYBE\nCONFIDENCE: HIGH\nREASONING: Something."
        v, c, r = _parse_feasibility_response(text)
        assert v == "UNKNOWN"

    def test_invalid_confidence_defaults_to_low(self):
        text = "VERDICT: REACHABLE\nCONFIDENCE: VERY_HIGH\nREASONING: Something."
        v, c, r = _parse_feasibility_response(text)
        assert c == "LOW"

    def test_empty_string_returns_defaults(self):
        v, c, r = _parse_feasibility_response("")
        assert v == "UNKNOWN"
        assert c == "LOW"
        assert "parse" in r.lower()

    def test_case_insensitive_verdict(self):
        text = "VERDICT: reachable\nCONFIDENCE: high\nREASONING: ok"
        v, c, r = _parse_feasibility_response(text)
        assert v == "REACHABLE"
        assert c == "HIGH"

    def test_extra_whitespace_handled(self):
        text = "  VERDICT:  REACHABLE  \n  CONFIDENCE:  HIGH  \n  REASONING:  All good.  "
        v, c, r = _parse_feasibility_response(text)
        assert v == "REACHABLE"

    def test_missing_reasoning_line(self):
        text = "VERDICT: REACHABLE\nCONFIDENCE: HIGH"
        v, c, r = _parse_feasibility_response(text)
        assert v == "REACHABLE"
        assert "parse" in r.lower()


# ── PathFeasibilityValidator.is_eligible ──────────────────────────────────────


class TestIsEligible:
    def test_high_security_is_eligible(self, validator, high_security_finding):
        assert validator.is_eligible(high_security_finding) is True

    def test_critical_security_is_eligible(self, validator):
        f = {"canonical_severity": "critical", "category": "security"}
        assert validator.is_eligible(f) is True

    def test_low_severity_not_eligible(self, validator, low_style_finding):
        assert validator.is_eligible(low_style_finding) is False

    def test_high_non_security_not_eligible(self, validator):
        f = {"canonical_severity": "high", "category": "style"}
        assert validator.is_eligible(f) is False

    def test_medium_security_not_eligible(self, validator):
        f = {"canonical_severity": "medium", "category": "security"}
        assert validator.is_eligible(f) is False

    def test_fallback_severity_key(self, validator):
        f = {"severity": "high", "category": "security"}
        assert validator.is_eligible(f) is True


# ── validate_async (mocked HTTP) ──────────────────────────────────────────────


class TestValidateAsync:
    def _mock_response(self, content: str):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"choices": [{"message": {"content": content}}]}
        return mock_resp

    @pytest.mark.asyncio
    async def test_validate_async_reachable(self, validator, high_security_finding):
        content = "VERDICT: REACHABLE\nCONFIDENCE: HIGH\nREASONING: Input flows to sink."
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=self._mock_response(content))
        result = await validator.validate_async(mock_client, high_security_finding, "code here", "fake-key")
        assert result.verdict == "REACHABLE"
        assert result.confidence == "HIGH"
        assert result.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_validate_async_unreachable(self, validator, high_security_finding):
        content = "VERDICT: UNREACHABLE\nCONFIDENCE: MEDIUM\nREASONING: Dead code path."
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=self._mock_response(content))
        result = await validator.validate_async(mock_client, high_security_finding, "code here", "fake-key")
        assert result.verdict == "UNREACHABLE"
        assert result.is_unreachable is True

    @pytest.mark.asyncio
    async def test_validate_async_http_error_returns_unknown(self, validator, high_security_finding):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("connection refused"))
        result = await validator.validate_async(mock_client, high_security_finding, "code", "fake-key")
        assert result.verdict == "UNKNOWN"
        assert result.confidence == "LOW"
        assert "connection refused" in result.reasoning

    @pytest.mark.asyncio
    async def test_validate_async_uses_fallback_keys(self, validator):
        """finding uses 'severity'/'file'/'line' fallback keys instead of canonical."""
        content = "VERDICT: UNKNOWN\nCONFIDENCE: LOW\nREASONING: No context."
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=self._mock_response(content))
        finding = {
            "severity": "high",
            "category": "security",
            "canonical_rule_id": "SEC-1",
            "file": "x.py",
            "line": 5,
            "message": "test",
        }
        result = await validator.validate_async(mock_client, finding, "", "fake-key")
        assert result.rule_id == "SEC-1"
        assert result.file_path == "x.py"
        assert result.line_number == 5

    @pytest.mark.asyncio
    async def test_validate_async_truncates_long_snippet(self, validator, high_security_finding):
        content = "VERDICT: REACHABLE\nCONFIDENCE: LOW\nREASONING: ok"
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=self._mock_response(content))
        long_snippet = "x" * 1000
        result = await validator.validate_async(mock_client, high_security_finding, long_snippet, "fake-key")
        # Should not crash — snippet is truncated to 500 chars in prompt
        assert result.verdict == "REACHABLE"


# ── validate_batch_async (mocked) ─────────────────────────────────────────────


class TestValidateBatchAsync:
    @pytest.mark.asyncio
    async def test_ineligible_findings_return_none(self, validator, low_style_finding):
        items = [{"finding": low_style_finding, "snippet": "x = 1"}]
        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            results = await validator.validate_batch_async(items, "fake-key")
        assert results == [None]

    @pytest.mark.asyncio
    async def test_empty_batch_returns_empty(self, validator):
        results = await validator.validate_batch_async([], "fake-key")
        assert results == []


# ── validate_batch sync wrapper ───────────────────────────────────────────────


class TestValidateBatchSync:
    def test_sync_wrapper_empty(self, validator):
        results = validator.validate_batch([], "fake-key")
        assert results == []

    def test_sync_wrapper_ineligible_only(self, validator, low_style_finding):
        items = [{"finding": low_style_finding, "snippet": "pass"}]
        results = validator.validate_batch(items, "fake-key")
        assert results == [None]


# ── FEASIBILITY_PROMPT template ───────────────────────────────────────────────


class TestPromptTemplate:
    def test_prompt_contains_required_placeholders(self):
        for placeholder in ["{rule_id}", "{severity}", "{file_path}", "{line_number}", "{message}", "{code_snippet}"]:
            assert placeholder in FEASIBILITY_PROMPT

    def test_prompt_formats_correctly(self):
        filled = FEASIBILITY_PROMPT.format(
            rule_id="SECURITY-001",
            severity="high",
            file_path="app.py",
            line_number=42,
            message="SQL injection",
            code_snippet="query = input()",
        )
        assert "SECURITY-001" in filled
        assert "app.py" in filled
