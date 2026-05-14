"""Tests for Phase 3 — AI Triage Agent (mocked LLM responses)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from CORE.engines.triage_agent import (
    MAX_TOOL_CALLS,
    SKIP_REASON_DISABLED,
    SKIP_REASON_NO_KEY,
    TriageAgent,
    TriageResult,
    _call_tool,
    _parse_args,
    _verdict_to_delta,
    get_callers,
    get_function_body,
    get_imports,
    grep,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "taint"

_FINDING_HIGH = {
    "canonical_rule_id": "SECURITY-027",
    "severity": "high",
    "category": "security",
    "file": "app/views.py",
    "line": 42,
    "message": "SQL injection via cursor.execute with user input",
    "tool": "taint_analyzer",
}

_FINDING_LOW = {
    "canonical_rule_id": "PRINT-001",
    "severity": "low",
    "category": "style",
    "file": "app/utils.py",
    "line": 10,
    "message": "print() in production code",
    "tool": "ruff",
}


def _mock_completion(content: str) -> MagicMock:
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    comp = MagicMock()
    comp.choices = [choice]
    return comp


def _mock_pool(response: str, has_keys: bool = True) -> MagicMock:
    """Build a mock KeyPool whose next_client().chat.completions.create returns response."""
    client = MagicMock()
    client.chat.completions.create.return_value = _mock_completion(response)
    pool = MagicMock()
    pool.has_keys = has_keys
    pool._model_override = None
    pool.next_client.return_value = client
    return pool


def _agent(response: str = "VERDICT: TRUE_POSITIVE\nREASONING: ok.", has_keys: bool = True) -> TriageAgent:
    return TriageAgent(_key_pool=_mock_pool(response, has_keys=has_keys))


# ---------------------------------------------------------------------------
# TriageResult
# ---------------------------------------------------------------------------


class TestTriageResult:
    def test_to_dict_keys(self):
        r = TriageResult("TRUE_POSITIVE", "Confirmed SQL injection.", 0.15, 2, 300)
        d = r.to_dict()
        assert d["triage_verdict"] == "TRUE_POSITIVE"
        assert d["triage_reasoning"] == "Confirmed SQL injection."
        assert d["triage_confidence_delta"] == 0.15
        assert d["triage_tool_calls"] == 2

    def test_skipped_factory(self):
        r = TriageResult.skipped(SKIP_REASON_NO_KEY)
        assert r.skip_reason == SKIP_REASON_NO_KEY
        assert r.verdict == "NEEDS_REVIEW"
        assert r.confidence_delta == 0.0

    def test_verdict_delta_true_positive(self):
        assert _verdict_to_delta("TRUE_POSITIVE") == pytest.approx(0.15)

    def test_verdict_delta_false_positive(self):
        assert _verdict_to_delta("FALSE_POSITIVE") == pytest.approx(-0.30)

    def test_verdict_delta_needs_review(self):
        assert _verdict_to_delta("NEEDS_REVIEW") == pytest.approx(0.0)

    def test_verdict_delta_unknown(self):
        assert _verdict_to_delta("UNKNOWN") == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Tool functions (local, no LLM)
# ---------------------------------------------------------------------------


class TestLocalTools:
    def test_get_imports_from_fixture(self):
        result = get_imports(str(FIXTURE_DIR / "direct_sqli.py"))
        assert "sqlite3" in result
        assert "flask" in result.lower() or "request" in result

    def test_get_imports_missing_file(self):
        result = get_imports("/nonexistent/file.py")
        assert "Error" in result

    def test_get_function_body_found(self):
        result = get_function_body(str(FIXTURE_DIR / "direct_sqli.py"), "search")
        assert "cursor.execute" in result

    def test_get_function_body_not_found(self):
        result = get_function_body(str(FIXTURE_DIR / "direct_sqli.py"), "nonexistent_func")
        assert "not found" in result.lower()

    def test_get_function_body_missing_file(self):
        result = get_function_body("/no/such/file.py", "f")
        assert "Error" in result

    def test_grep_finds_match(self, tmp_path):
        (tmp_path / "sample.py").write_text("def unsafe(): cursor.execute(query)\n")
        result = grep("cursor.execute", str(tmp_path))
        assert "cursor.execute" in result

    def test_grep_no_match(self, tmp_path):
        (tmp_path / "sample.py").write_text("def safe(): pass\n")
        result = grep("cursor.execute", str(tmp_path))
        assert "No matches" in result

    def test_get_callers_finds_call(self, tmp_path):
        (tmp_path / "caller.py").write_text("def run(): search(db)\n")
        result = get_callers("search", str(tmp_path))
        assert "search" in result

    def test_get_callers_none_found(self, tmp_path):
        (tmp_path / "code.py").write_text("def unrelated(): pass\n")
        result = get_callers("nonexistent_fn", str(tmp_path))
        assert "No callers" in result


class TestParseArgs:
    def test_simple_args(self):
        assert _parse_args("app/views.py, search") == ["app/views.py", "search"]

    def test_quoted_args(self):
        assert _parse_args("'app/views.py', 'search'") == ["app/views.py", "search"]

    def test_single_arg(self):
        assert _parse_args("app/views.py") == ["app/views.py"]

    def test_empty_args(self):
        assert _parse_args("") == []


class TestCallTool:
    def test_unknown_tool(self):
        result = _call_tool("nonexistent", "", None)
        assert "Unknown tool" in result

    def test_get_imports_dispatch(self, tmp_path):
        f = tmp_path / "mod.py"
        f.write_text("import os\n")
        result = _call_tool("get_imports", str(f), None)
        assert "os" in result

    def test_grep_dispatch(self, tmp_path):
        (tmp_path / "code.py").write_text("import hashlib\n")
        result = _call_tool("grep", f"hashlib,{tmp_path}", str(tmp_path))
        assert "hashlib" in result


# ---------------------------------------------------------------------------
# TriageAgent unit tests (mock-injected pool)
# ---------------------------------------------------------------------------


class TestTriageAgentSkip:
    def test_skips_when_no_keys(self):
        agent = _agent(has_keys=False)
        result = agent.triage(_FINDING_HIGH)
        assert result.skip_reason == SKIP_REASON_NO_KEY

    def test_skips_when_disabled_env(self, monkeypatch):
        monkeypatch.setenv("ACRQA_TRIAGE_AGENT", "0")
        agent = _agent()
        result = agent.triage(_FINDING_HIGH)
        assert result.skip_reason == SKIP_REASON_DISABLED

    def test_is_available_true_when_keys(self):
        agent = _agent()
        assert agent.is_available is True

    def test_is_available_false_no_keys(self):
        agent = _agent(has_keys=False)
        assert agent.is_available is False


class TestTriageAgentVerdicts:
    def test_direct_true_positive(self):
        agent = _agent("VERDICT: TRUE_POSITIVE\nREASONING: User input directly reaches cursor.execute.")
        result = agent.triage(_FINDING_HIGH)
        assert result.verdict == "TRUE_POSITIVE"
        assert result.confidence_delta == pytest.approx(0.15)
        assert "cursor.execute" in result.reasoning

    def test_false_positive_verdict(self):
        agent = _agent("VERDICT: FALSE_POSITIVE\nREASONING: The input is validated before use.")
        result = agent.triage(_FINDING_HIGH)
        assert result.verdict == "FALSE_POSITIVE"
        assert result.confidence_delta == pytest.approx(-0.30)

    def test_needs_review_verdict(self):
        agent = _agent("VERDICT: NEEDS_REVIEW\nREASONING: Insufficient context to determine.")
        result = agent.triage(_FINDING_HIGH)
        assert result.verdict == "NEEDS_REVIEW"
        assert result.confidence_delta == pytest.approx(0.0)

    def test_verdict_case_insensitive(self):
        agent = _agent("verdict: true_positive\nreasoning: clear taint flow.")
        result = agent.triage(_FINDING_HIGH)
        assert result.verdict == "TRUE_POSITIVE"

    def test_no_verdict_defaults_needs_review(self):
        agent = _agent("This looks suspicious but I can't say for sure.")
        result = agent.triage(_FINDING_HIGH)
        assert result.verdict == "NEEDS_REVIEW"

    def test_reasoning_extracted(self):
        agent = _agent("VERDICT: FALSE_POSITIVE\nREASONING: Input is sanitized by validate().")
        result = agent.triage(_FINDING_HIGH)
        assert "sanitized" in result.reasoning

    def test_latency_is_non_negative(self):
        agent = _agent("VERDICT: TRUE_POSITIVE\nREASONING: direct flow.")
        result = agent.triage(_FINDING_HIGH)
        assert result.latency_ms >= 0

    def test_code_snippet_passed_in(self):
        pool = _mock_pool("VERDICT: TRUE_POSITIVE\nREASONING: snippet confirms.")
        agent = TriageAgent(_key_pool=pool)
        agent.triage(_FINDING_HIGH, code_snippet="x = request.args.get('q')\ncursor.execute(x)")
        call_args = pool.next_client().chat.completions.create.call_args
        messages = call_args[1]["messages"] if "messages" in call_args[1] else call_args[0][0]
        user_msg = next(m["content"] for m in messages if m["role"] == "user")
        assert "cursor.execute" in user_msg


class TestTriageAgentToolLoop:
    def test_one_tool_call_then_verdict(self):
        tool_reply = "TOOL: get_imports(app/views.py)"
        verdict_reply = "VERDICT: TRUE_POSITIVE\nREASONING: request is imported directly."
        client = MagicMock()
        client.chat.completions.create.side_effect = [
            _mock_completion(tool_reply),
            _mock_completion(verdict_reply),
        ]
        pool = MagicMock()
        pool.has_keys = True
        pool._model_override = None
        pool.next_client.return_value = client

        with patch("CORE.engines.triage_agent._call_tool", return_value="import flask"):
            agent = TriageAgent(_key_pool=pool)
            result = agent.triage(_FINDING_HIGH, target_dir="/tmp")

        assert result.verdict == "TRUE_POSITIVE"
        assert result.tool_calls_used == 1

    def test_tool_calls_capped_at_max(self):
        tool_reply = "TOOL: grep(cursor.execute, /tmp)"
        client = MagicMock()
        client.chat.completions.create.return_value = _mock_completion(tool_reply)
        pool = MagicMock()
        pool.has_keys = True
        pool._model_override = None
        pool.next_client.return_value = client

        with patch("CORE.engines.triage_agent._call_tool", return_value="no match"):
            agent = TriageAgent(_key_pool=pool)
            result = agent.triage(_FINDING_HIGH)

        assert result.tool_calls_used <= MAX_TOOL_CALLS

    def test_llm_error_returns_needs_review(self):
        client = MagicMock()
        client.chat.completions.create.side_effect = RuntimeError("API down")
        pool = MagicMock()
        pool.has_keys = True
        pool._model_override = None
        pool.next_client.return_value = client
        agent = TriageAgent(_key_pool=pool)
        result = agent.triage(_FINDING_HIGH)
        assert result.verdict == "NEEDS_REVIEW"

    def test_two_tool_calls_then_verdict(self):
        calls = [
            _mock_completion("TOOL: get_imports(app/views.py)"),
            _mock_completion("TOOL: get_function_body(app/views.py, search)"),
            _mock_completion("VERDICT: TRUE_POSITIVE\nREASONING: confirmed."),
        ]
        client = MagicMock()
        client.chat.completions.create.side_effect = calls
        pool = MagicMock()
        pool.has_keys = True
        pool._model_override = None
        pool.next_client.return_value = client

        with patch("CORE.engines.triage_agent._call_tool", return_value="some result"):
            agent = TriageAgent(_key_pool=pool)
            result = agent.triage(_FINDING_HIGH)

        assert result.verdict == "TRUE_POSITIVE"
        assert result.tool_calls_used == 2


class TestEnrichFindings:
    def test_enrich_high_security_findings(self):
        findings = [_FINDING_HIGH.copy(), _FINDING_LOW.copy()]
        agent = _agent("VERDICT: TRUE_POSITIVE\nREASONING: confirmed.")
        enriched = agent.enrich_findings(findings)
        high = next(f for f in enriched if f.get("canonical_rule_id") == "SECURITY-027")
        low = next(f for f in enriched if f.get("canonical_rule_id") == "PRINT-001")
        assert high.get("triage_verdict") == "TRUE_POSITIVE"
        assert "triage_verdict" not in low

    def test_enrich_skips_when_no_keys(self):
        agent = _agent(has_keys=False)
        findings = [_FINDING_HIGH.copy()]
        enriched = agent.enrich_findings(findings)
        assert "triage_verdict" not in enriched[0]

    def test_enrich_empty_findings(self):
        agent = _agent()
        enriched = agent.enrich_findings([])
        assert enriched == []

    def test_enrich_no_eligible_findings(self):
        agent = _agent()
        enriched = agent.enrich_findings([_FINDING_LOW.copy()])
        assert "triage_verdict" not in enriched[0]

    def test_enrich_uses_snippet_from_snippets_dict(self):
        finding = {**_FINDING_HIGH, "file": "app/views.py"}
        snippets = {"app/views.py": "x = request.args.get('q')\ncursor.execute(x)"}
        agent = _agent("VERDICT: TRUE_POSITIVE\nREASONING: snippet confirms.")
        enriched = agent.enrich_findings([finding], snippets=snippets)
        assert enriched[0].get("triage_verdict") == "TRUE_POSITIVE"

    def test_enrich_handles_per_finding_exception(self):
        client = MagicMock()
        client.chat.completions.create.side_effect = Exception("boom")
        pool = MagicMock()
        pool.has_keys = True
        pool._model_override = None
        pool.next_client.return_value = client
        agent = TriageAgent(_key_pool=pool)
        enriched = agent.enrich_findings([_FINDING_HIGH.copy()])
        assert isinstance(enriched, list)

    def test_enrich_multiple_high_findings(self):
        f1 = {**_FINDING_HIGH, "file": "a.py", "line": 1}
        f2 = {**_FINDING_HIGH, "file": "b.py", "line": 2}
        agent = _agent("VERDICT: TRUE_POSITIVE\nREASONING: both confirmed.")
        enriched = agent.enrich_findings([f1, f2])
        assert all(f.get("triage_verdict") == "TRUE_POSITIVE" for f in enriched)

    def test_enrich_false_positive_delta_applied(self):
        agent = _agent("VERDICT: FALSE_POSITIVE\nREASONING: guarded by sanitizer.")
        findings = [_FINDING_HIGH.copy()]
        enriched = agent.enrich_findings(findings)
        assert enriched[0]["triage_confidence_delta"] == pytest.approx(-0.30)
