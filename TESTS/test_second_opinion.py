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
        engine = SecondOpinionEngine()
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
