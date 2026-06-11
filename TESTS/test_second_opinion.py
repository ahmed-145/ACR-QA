"""Tests for the Second Opinion engine (v5.0.0 Phase A.5)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from starlette.testclient import TestClient

from CORE.engines.second_opinion import (
    VALID_VERDICTS,
    SecondOpinionEngine,
    SecondOpinionResult,
    _OllamaUnavailableError,
    agreement_rate,
    parse_verdict,
)
from FRONTEND.api.deps import get_current_user, get_db
from FRONTEND.api.main import app as fastapi_app

# ── parse_verdict ─────────────────────────────────────────────────────────────


class TestParseVerdict:
    def test_extracts_tp(self):
        v, r = parse_verdict("TP\nThis is a real eval() call from user input.")
        assert v == "TP"
        assert "eval" in r.lower()

    def test_extracts_fp(self):
        v, r = parse_verdict("FP — variable is a literal here, not tainted.")
        assert v == "FP"

    def test_extracts_needs_review(self):
        v, r = parse_verdict("NEEDS_REVIEW: requires data-flow context.")
        assert v == "NEEDS_REVIEW"

    def test_falls_back_to_needs_review_on_no_token(self):
        v, _ = parse_verdict("I don't know.")
        assert v == "NEEDS_REVIEW"

    def test_lowercase_inputs_normalised(self):
        v, _ = parse_verdict("tp this looks real")
        assert v == "TP"

    def test_empty_input(self):
        v, r = parse_verdict("")
        assert v == "NEEDS_REVIEW"
        assert r == ""

    def test_reason_capped_at_200_chars(self):
        long_reason = "x" * 500
        v, r = parse_verdict(f"TP\n{long_reason}")
        assert len(r) <= 200


# ── SecondOpinionEngine.review (mocked providers) ────────────────────────────


@pytest.fixture
def finding() -> dict:
    return {
        "id": 7,
        "canonical_rule_id": "SECURITY-001",
        "canonical_severity": "high",
        "file_path": "app.py",
        "line_number": 42,
        "message": "Use of eval() with attacker-controlled input",
        "code_snippet": "result = eval(request.args['x'])",
    }


class TestSecondOpinionAgreement:
    def test_both_agree_tp(self, finding):
        engine = SecondOpinionEngine()
        with patch.object(SecondOpinionEngine, "_call_provider") as mock:
            mock.side_effect = [("TP", "real eval call"), ("TP", "matches the pattern")]
            r = engine.review(finding)
        assert r.primary_verdict == "TP"
        assert r.secondary_verdict == "TP"
        assert r.agreement is True
        assert r.confidence_delta == 15
        assert r.skipped_reason is None

    def test_both_agree_fp(self, finding):
        engine = SecondOpinionEngine()
        with patch.object(SecondOpinionEngine, "_call_provider") as mock:
            mock.side_effect = [("FP", "x is a literal"), ("FP", "no taint flow")]
            r = engine.review(finding)
        assert r.agreement is True
        assert r.confidence_delta == 15

    def test_disagreement_lowers_confidence(self, finding):
        engine = SecondOpinionEngine()
        with patch.object(SecondOpinionEngine, "_call_provider") as mock:
            mock.side_effect = [("TP", "looks real"), ("FP", "not actually tainted")]
            r = engine.review(finding)
        assert r.agreement is False
        assert r.confidence_delta == -10

    def test_both_needs_review_is_zero_delta(self, finding):
        engine = SecondOpinionEngine()
        with patch.object(SecondOpinionEngine, "_call_provider") as mock:
            mock.side_effect = [
                ("NEEDS_REVIEW", "uncertain"),
                ("NEEDS_REVIEW", "uncertain too"),
            ]
            r = engine.review(finding)
        # Both agree but verdict isn't TP/FP → no confidence boost
        assert r.agreement is True
        assert r.confidence_delta == 0


# ── Provider failures ─────────────────────────────────────────────────────────


class TestProviderFailures:
    def test_ollama_unavailable_does_not_break(self, finding):
        # Use explicit secondary="ollama" so test is provider-agnostic from defaults
        engine = SecondOpinionEngine(secondary="ollama")
        call_count = [0]

        def fake_call(self, provider, prompt):
            call_count[0] += 1
            if provider == "groq":
                return ("TP", "real")
            raise _OllamaUnavailableError("connection refused")

        with patch.object(SecondOpinionEngine, "_call_provider", fake_call):
            r = engine.review(finding)
        assert r.primary_verdict == "TP"
        assert r.skipped_reason is not None
        assert "ollama" in r.skipped_reason.lower()
        assert r.confidence_delta == 0

    def test_gemini_unavailable_falls_back_gracefully(self, finding):
        """Gemini missing key → skipped_reason set, confidence_delta=0, no crash."""
        engine = SecondOpinionEngine(secondary="gemini")

        def fake_call(self, provider, prompt):
            if provider == "groq":
                return ("TP", "real groq verdict")
            from CORE.engines.second_opinion import _GeminiUnavailableError, _OllamaUnavailableError

            if provider == "gemini":
                raise _GeminiUnavailableError("GEMINI_API_KEY not set")
            raise _OllamaUnavailableError("ollama not running either")

        with patch.object(SecondOpinionEngine, "_call_provider", fake_call):
            r = engine.review(finding)
        assert r.primary_verdict == "TP"
        assert r.skipped_reason is not None
        assert r.confidence_delta == 0

    def test_primary_failure_returns_safe_default(self, finding):
        engine = SecondOpinionEngine()

        def fake_call(self, provider, prompt):
            raise RuntimeError("no key")

        with patch.object(SecondOpinionEngine, "_call_provider", fake_call):
            r = engine.review(finding)
        assert r.primary_verdict == "NEEDS_REVIEW"
        assert r.skipped_reason == "primary_unavailable"
        assert r.confidence_delta == 0


# ── Result types ─────────────────────────────────────────────────────────────


class TestSerialization:
    def test_to_dict_shape(self):
        r = SecondOpinionResult(
            finding_id=1,
            primary_provider="groq",
            primary_verdict="TP",
            primary_reason="x",
            secondary_provider="ollama",
            secondary_verdict="TP",
            secondary_reason="y",
            agreement=True,
            confidence_delta=15,
        )
        d = r.to_dict()
        assert d["agreement"] is True
        assert set(d.keys()) >= {
            "finding_id",
            "primary_provider",
            "primary_verdict",
            "secondary_verdict",
            "agreement",
            "confidence_delta",
        }


class TestAgreementRate:
    def test_empty_returns_zero(self):
        r = agreement_rate([])
        assert r["agreement_rate"] == 0.0

    def test_all_agree(self):
        results = [
            SecondOpinionResult(
                finding_id=i,
                primary_provider="groq",
                primary_verdict="TP",
                primary_reason="",
                secondary_provider="ollama",
                secondary_verdict="TP",
                secondary_reason="",
                agreement=True,
                confidence_delta=15,
            )
            for i in range(5)
        ]
        r = agreement_rate(results)
        assert r["agreement_rate"] == 1.0
        assert r["scored"] == 5

    def test_skipped_excluded_from_rate(self):
        results = [
            SecondOpinionResult(
                finding_id=1,
                primary_provider="groq",
                primary_verdict="TP",
                primary_reason="",
                secondary_provider="ollama",
                secondary_verdict="TP",
                secondary_reason="",
                agreement=True,
                confidence_delta=15,
            ),
            SecondOpinionResult(
                finding_id=2,
                primary_provider="groq",
                primary_verdict="TP",
                primary_reason="",
                secondary_provider="ollama",
                secondary_verdict="NEEDS_REVIEW",
                secondary_reason="",
                agreement=False,
                confidence_delta=0,
                skipped_reason="ollama_unavailable",
            ),
        ]
        r = agreement_rate(results)
        assert r["scored"] == 1
        assert r["skipped"] == 1
        assert r["agreement_rate"] == 1.0


# ── Endpoint ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def client():
    mock_db = MagicMock()
    mock_user = {"id": 1, "email": "u@x.local", "role": "admin"}
    fastapi_app.dependency_overrides[get_db] = lambda: mock_db
    fastapi_app.dependency_overrides[get_current_user] = lambda: mock_user
    with TestClient(fastapi_app, raise_server_exceptions=False) as c:
        yield c, mock_db
    fastapi_app.dependency_overrides.clear()


class TestEndpoint:
    def test_404_when_finding_missing(self, client):
        c, db = client
        db.get_finding_by_id.return_value = None
        r = c.post("/v1/findings/999/second-opinion")
        assert r.status_code == 404

    def test_returns_verdict_payload(self, client, finding):
        c, db = client
        db.get_finding_by_id.return_value = finding
        with patch.object(SecondOpinionEngine, "_call_provider") as mock:
            mock.side_effect = [("TP", "real"), ("TP", "matches")]
            r = c.post(f"/v1/findings/{finding['id']}/second-opinion")
        assert r.status_code == 200
        body = r.json()
        assert body["agreement"] is True
        assert body["primary_verdict"] == "TP"
        assert body["secondary_verdict"] == "TP"

    def test_endpoint_handles_ollama_skip(self, client, finding):
        c, db = client
        db.get_finding_by_id.return_value = finding

        def fake_call(self, provider, prompt):
            if provider == "groq":
                return ("TP", "real")
            raise _OllamaUnavailableError("connection refused")

        with patch.object(SecondOpinionEngine, "_call_provider", fake_call):
            r = c.post(f"/v1/findings/{finding['id']}/second-opinion")
        assert r.status_code == 200
        body = r.json()
        assert body["primary_verdict"] == "TP"
        assert body["skipped_reason"]


class TestQuotaEnforcement:
    def test_429_when_quota_exceeded(self, client, finding):
        c, db = client
        db.get_finding_by_id.return_value = finding
        db.check_quota.return_value = (
            False,
            {"tokens_used_today": 100_001, "daily_limit": 100_000},
        )
        r = c.post(f"/v1/findings/{finding['id']}/second-opinion")
        assert r.status_code == 429
        body = r.json()
        assert body["detail"]["error"] == "daily_quota_exceeded"

    def test_200_when_within_quota(self, client, finding):
        c, db = client
        db.get_finding_by_id.return_value = finding
        db.check_quota.return_value = (
            True,
            {"tokens_used_today": 5_000, "daily_limit": 100_000},
        )
        with patch.object(SecondOpinionEngine, "_call_provider") as mock:
            mock.side_effect = [("TP", "real"), ("TP", "matches")]
            r = c.post(f"/v1/findings/{finding['id']}/second-opinion")
        assert r.status_code == 200

    def test_proceeds_when_quota_table_missing(self, client, finding):
        """Quota check must degrade gracefully on older deployments."""
        c, db = client
        db.get_finding_by_id.return_value = finding
        db.check_quota.side_effect = Exception("relation user_quota does not exist")
        with patch.object(SecondOpinionEngine, "_call_provider") as mock:
            mock.side_effect = [("FP", "literal"), ("FP", "no taint")]
            r = c.post(f"/v1/findings/{finding['id']}/second-opinion")
        assert r.status_code == 200


class TestVerdictVocabularyConstant:
    def test_constant_locked_to_three(self):
        assert VALID_VERDICTS == ("TP", "FP", "NEEDS_REVIEW")


# ── parse_verdict non-string guard ────────────────────────────────────────────


class TestParseVerdictNonString:
    def test_non_string_returns_needs_review(self):
        from CORE.engines.second_opinion import parse_verdict

        v, r = parse_verdict(None)  # type: ignore[arg-type]
        assert v == "NEEDS_REVIEW"
        assert r == ""

    def test_integer_returns_needs_review(self):
        from CORE.engines.second_opinion import parse_verdict

        v, r = parse_verdict(42)  # type: ignore[arg-type]
        assert v == "NEEDS_REVIEW"


# ── _call_gemini ──────────────────────────────────────────────────────────────


class TestCallGemini:
    def test_returns_content_on_200(self):
        from unittest.mock import MagicMock

        from CORE.engines.second_opinion import _call_gemini

        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {"candidates": [{"content": {"parts": [{"text": "TP\nreal eval call"}]}}]}
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            with patch("httpx.Client") as mock_client:
                mock_client.return_value.__enter__.return_value.post.return_value = fake_resp
                result = _call_gemini("is this a vuln?")
        assert result == "TP\nreal eval call"

    def test_raises_on_non_200(self):
        from unittest.mock import MagicMock

        from CORE.engines.second_opinion import _call_gemini, _GeminiUnavailableError

        fake_resp = MagicMock()
        fake_resp.status_code = 429
        fake_resp.text = "rate limited"
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            with patch("httpx.Client") as mock_client:
                mock_client.return_value.__enter__.return_value.post.return_value = fake_resp
                with pytest.raises(_GeminiUnavailableError, match="429"):
                    _call_gemini("prompt")

    def test_raises_on_malformed_response(self):
        from unittest.mock import MagicMock

        from CORE.engines.second_opinion import _call_gemini, _GeminiUnavailableError

        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {"candidates": []}  # missing content
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            with patch("httpx.Client") as mock_client:
                mock_client.return_value.__enter__.return_value.post.return_value = fake_resp
                with pytest.raises(_GeminiUnavailableError, match="malformed"):
                    _call_gemini("prompt")

    def test_raises_on_http_error(self):
        import httpx

        from CORE.engines.second_opinion import _call_gemini, _GeminiUnavailableError

        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            with patch("httpx.Client") as mock_client:
                mock_client.return_value.__enter__.return_value.post.side_effect = httpx.HTTPError("connection refused")
                with pytest.raises(_GeminiUnavailableError, match="http error"):
                    _call_gemini("prompt")

    def test_raises_when_no_api_key(self):
        from CORE.engines.second_opinion import _call_gemini, _GeminiUnavailableError

        with patch.dict("os.environ", {}, clear=True):
            import os

            os.environ.pop("GEMINI_API_KEY", None)
            os.environ.pop("GOOGLE_AI_API_KEY", None)
            with pytest.raises(_GeminiUnavailableError, match="not set"):
                _call_gemini("prompt")


# ── _call_ollama ──────────────────────────────────────────────────────────────


class TestCallOllama:
    def test_returns_content_on_200(self):
        from unittest.mock import MagicMock

        from CORE.engines.second_opinion import _call_ollama

        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {"choices": [{"message": {"content": "FP — literal"}}]}
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.return_value = fake_resp
            result = _call_ollama("prompt")
        assert result == "FP — literal"

    def test_raises_on_non_200(self):
        from unittest.mock import MagicMock

        from CORE.engines.second_opinion import _call_ollama, _OllamaUnavailableError

        fake_resp = MagicMock()
        fake_resp.status_code = 503
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.return_value = fake_resp
            with pytest.raises(_OllamaUnavailableError, match="503"):
                _call_ollama("prompt")

    def test_raises_on_http_error(self):
        import httpx

        from CORE.engines.second_opinion import _call_ollama, _OllamaUnavailableError

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.side_effect = httpx.HTTPError("connection refused")
            with pytest.raises(_OllamaUnavailableError, match="http error"):
                _call_ollama("prompt")

    def test_raises_on_malformed_json(self):
        from unittest.mock import MagicMock

        from CORE.engines.second_opinion import _call_ollama, _OllamaUnavailableError

        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {}  # missing choices
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.return_value = fake_resp
            with pytest.raises(_OllamaUnavailableError, match="malformed"):
                _call_ollama("prompt")


# ── _call_groq ────────────────────────────────────────────────────────────────


class TestCallGroq:
    def test_raises_when_no_keys(self):
        from unittest.mock import MagicMock

        from CORE.engines.second_opinion import _call_groq

        key_pool = MagicMock()
        key_pool.has_keys = False
        with pytest.raises(RuntimeError, match="No Groq key"):
            _call_groq("prompt", key_pool=key_pool)

    def test_returns_content_string(self):
        from unittest.mock import MagicMock

        from CORE.engines.second_opinion import _call_groq

        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content="TP\nreal vuln"))
        ]
        key_pool = MagicMock()
        key_pool.has_keys = True
        key_pool.next_client.return_value = fake_client
        result = _call_groq("prompt", key_pool=key_pool)
        assert result == "TP\nreal vuln"

    def test_returns_empty_string_on_none_content(self):
        from unittest.mock import MagicMock

        from CORE.engines.second_opinion import _call_groq

        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value.choices = [MagicMock(message=MagicMock(content=None))]
        key_pool = MagicMock()
        key_pool.has_keys = True
        key_pool.next_client.return_value = fake_client
        result = _call_groq("prompt", key_pool=key_pool)
        assert result == ""

    def test_returns_empty_string_on_attribute_error(self):
        from unittest.mock import MagicMock

        from CORE.engines.second_opinion import _call_groq

        fake_client = MagicMock()
        # choices is an empty list → IndexError on [0]
        fake_client.chat.completions.create.return_value.choices = []
        key_pool = MagicMock()
        key_pool.has_keys = True
        key_pool.next_client.return_value = fake_client
        result = _call_groq("prompt", key_pool=key_pool)
        assert result == ""

    def test_default_key_pool_created_when_none(self):
        """When key_pool=None, KeyPool is created internally; no-keys path still works."""
        from unittest.mock import MagicMock

        from CORE.engines.second_opinion import _call_groq

        mock_pool = MagicMock()
        mock_pool.has_keys = False
        with patch("CORE.engines.explainer.KeyPool", return_value=mock_pool):
            with pytest.raises(RuntimeError, match="No Groq key"):
                _call_groq("prompt", key_pool=None)


# ── _call_provider dispatch ───────────────────────────────────────────────────


class TestCallProviderDispatch:
    def test_groq_path(self, finding):
        from CORE.engines.second_opinion import SecondOpinionEngine

        engine = SecondOpinionEngine()
        with patch("CORE.engines.second_opinion._call_groq", return_value="TP\nreal") as m:
            v, r = engine._call_provider("groq", "prompt")
        m.assert_called_once()
        assert v == "TP"

    def test_gemini_path(self, finding):
        from CORE.engines.second_opinion import SecondOpinionEngine

        engine = SecondOpinionEngine()
        with patch("CORE.engines.second_opinion._call_gemini", return_value="FP\nno taint") as m:
            v, r = engine._call_provider("gemini", "prompt")
        m.assert_called_once()
        assert v == "FP"

    def test_ollama_path(self, finding):
        from CORE.engines.second_opinion import SecondOpinionEngine

        engine = SecondOpinionEngine()
        with patch("CORE.engines.second_opinion._call_ollama", return_value="NEEDS_REVIEW") as m:
            v, r = engine._call_provider("ollama", "prompt")
        m.assert_called_once()
        assert v == "NEEDS_REVIEW"

    def test_unknown_provider_raises(self, finding):
        from CORE.engines.second_opinion import SecondOpinionEngine

        engine = SecondOpinionEngine()
        with pytest.raises(ValueError, match="unknown provider"):
            engine._call_provider("anthropic", "prompt")


# ── Gemini-fail → Ollama-fallback path ────────────────────────────────────────


class TestGeminiFallbackToOllama:
    def test_gemini_fail_ollama_succeeds(self, finding):
        """Gemini fails → engine tries ollama → success → skipped_reason cleared."""
        from CORE.engines.second_opinion import (
            SecondOpinionEngine,
            _GeminiUnavailableError,
        )

        engine = SecondOpinionEngine(secondary="gemini")

        def fake_call(self, provider, prompt):
            if provider == "groq":
                return ("TP", "real groq")
            if provider == "gemini":
                raise _GeminiUnavailableError("no key")
            if provider == "ollama":
                return ("TP", "ollama agrees")
            raise ValueError("unexpected")

        with patch.object(SecondOpinionEngine, "_call_provider", fake_call):
            r = engine.review(finding)
        assert r.primary_verdict == "TP"
        assert r.secondary_verdict == "TP"
        assert r.skipped_reason is None  # fallback succeeded

    def test_gemini_fail_ollama_also_fails(self, finding):
        """Both cloud and local secondary fail → skipped_reason set, no crash."""
        from CORE.engines.second_opinion import (
            SecondOpinionEngine,
            _GeminiUnavailableError,
            _OllamaUnavailableError,
        )

        engine = SecondOpinionEngine(secondary="gemini")

        def fake_call(self, provider, prompt):
            if provider == "groq":
                return ("FP", "literal value")
            if provider == "gemini":
                raise _GeminiUnavailableError("no key")
            raise _OllamaUnavailableError("not running")

        with patch.object(SecondOpinionEngine, "_call_provider", fake_call):
            r = engine.review(finding)
        assert r.skipped_reason is not None
        assert r.confidence_delta == 0

    def test_secondary_generic_exception(self, finding):
        """Unexpected exception from secondary → skipped_reason set gracefully."""
        from CORE.engines.second_opinion import SecondOpinionEngine

        engine = SecondOpinionEngine(secondary="ollama")

        def fake_call(self, provider, prompt):
            if provider == "groq":
                return ("TP", "real")
            raise ConnectionError("network down")

        with patch.object(SecondOpinionEngine, "_call_provider", fake_call):
            r = engine.review(finding)
        assert r.skipped_reason is not None
        assert "secondary_unavailable" in r.skipped_reason
