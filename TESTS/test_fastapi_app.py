"""
Ported god-mode tests for the FastAPI app — replaces legacy test_flask_app.py.

Tests _calculate_confidence (now CORE.confidence_utils.calculate_confidence)
and the FastAPI endpoints that replaced the old Flask /api/* routes.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from starlette.testclient import TestClient

from FRONTEND.api.deps import get_current_user, get_db
from FRONTEND.api.main import app as fastapi_app

# ─────────────────────────────────────────────────────────────
#  Fixtures
# ─────────────────────────────────────────────────────────────


@pytest.fixture()
def client():
    """TestClient with auth and DB mocked out."""
    mock_db = MagicMock()
    mock_user = {"id": 1, "email": "test@acrqa.local", "role": "admin"}

    fastapi_app.dependency_overrides[get_db] = lambda: mock_db
    fastapi_app.dependency_overrides[get_current_user] = lambda: mock_user

    with TestClient(fastapi_app, raise_server_exceptions=False) as c:
        yield c, mock_db

    fastapi_app.dependency_overrides.clear()


# ════════════════════════════════════════════════════════════
#  calculate_confidence (pure function — no HTTP client needed)
# ════════════════════════════════════════════════════════════


class TestCalculateConfidence:
    def _conf(self, finding):
        from CORE.confidence_utils import calculate_confidence

        return calculate_confidence(finding)

    def test_baseline_no_extras(self):
        assert self._conf({}) == 0.5

    def test_rule_cited_adds_02(self):
        score = self._conf(
            {
                "canonical_rule_id": "SEC-001",
                "explanation_text": "This violates SEC-001 because...",
            }
        )
        assert score >= 0.7

    def test_has_explanation_adds_01(self):
        assert self._conf({"explanation_text": "some explanation"}) >= 0.6

    def test_high_severity_adds_01(self):
        assert self._conf({"canonical_severity": "high"}) >= 0.6

    def test_security_category_adds_01(self):
        assert self._conf({"category": "security"}) >= 0.6

    def test_all_factors_capped_at_1(self):
        score = self._conf(
            {
                "canonical_rule_id": "X",
                "explanation_text": "violates X",
                "canonical_severity": "high",
                "category": "security",
            }
        )
        assert score <= 1.0

    def test_rounded_to_2_decimals(self):
        score = self._conf({"canonical_severity": "high"})
        assert score == round(score, 2)

    def test_explanation_field_alias_works(self):
        """Also accept 'explanation' key (Flask legacy field name)."""
        score = self._conf({"explanation": "something"})
        assert score >= 0.6


# ════════════════════════════════════════════════════════════
#  GET /health
# ════════════════════════════════════════════════════════════


class TestHealthEndpoint:
    def test_returns_200(self, client):
        c, _ = client
        assert c.get("/health").status_code == 200

    def test_returns_healthy(self, client):
        c, _ = client
        data = c.get("/health").json()
        assert data["status"] == "healthy"

    def test_returns_version(self, client):
        c, _ = client
        assert "version" in c.get("/health").json()


# ════════════════════════════════════════════════════════════
#  GET /v1/runs  (was /api/runs)
# ════════════════════════════════════════════════════════════


class TestGetRuns:
    def test_success_returns_runs_list(self, client):
        c, db = client
        db.get_recent_runs.return_value = [
            {"id": 1, "repo_name": "repo", "pr_number": None, "status": "complete", "started_at": "2024-01-01"}
        ]
        db.get_run_summary.return_value = {
            "findings_count": 5,
            "high_severity_count": 2,
            "medium_severity_count": 2,
            "low_severity_count": 1,
        }
        resp = c.get("/v1/runs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["runs"]) == 1
        assert data["runs"][0]["total_findings"] == 5

    def test_empty_db_returns_empty_list(self, client):
        c, db = client
        db.get_recent_runs.return_value = []
        resp = c.get("/v1/runs")
        assert resp.status_code == 200
        assert resp.json()["runs"] == []

    def test_custom_limit_param(self, client):
        c, db = client
        db.get_recent_runs.return_value = []
        c.get("/v1/runs?limit=5")
        db.get_recent_runs.assert_called_once_with(limit=5)

    def test_no_summary_defaults_to_zero(self, client):
        c, db = client
        db.get_recent_runs.return_value = [
            {"id": 1, "repo_name": "r", "pr_number": None, "status": "complete", "started_at": "2024-01-01"}
        ]
        db.get_run_summary.return_value = None
        data = c.get("/v1/runs").json()
        assert data["runs"][0]["total_findings"] == 0


# ════════════════════════════════════════════════════════════
#  GET /v1/runs/{id}/findings  (was /api/runs/<id>/findings)
# ════════════════════════════════════════════════════════════


class TestGetRunFindings:
    def _finding(self, rule_id="SEC-001", sev="high", cat="security", file_path="app.py", line=10):
        return {
            "id": 1,
            "canonical_rule_id": rule_id,
            "canonical_severity": sev,
            "category": cat,
            "file_path": file_path,
            "line_number": line,
            "message": "test",
            "explanation_text": None,
            "model_name": None,
            "latency_ms": None,
            "tool": "bandit",
            "confidence_score": None,
            "ground_truth": None,
            "rule_id": rule_id,
        }

    def test_success(self, client):
        c, db = client
        db.get_findings_with_explanations.return_value = [self._finding()]
        resp = c.get("/v1/runs/1/findings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["total"] == 1

    def test_severity_filter(self, client):
        c, db = client
        db.get_findings_with_explanations.return_value = [
            self._finding(sev="high"),
            self._finding(sev="low"),
        ]
        data = c.get("/v1/runs/1/findings?severity=high").json()
        assert data["total"] == 1
        assert data["findings"][0]["severity"] == "high"

    def test_category_filter(self, client):
        c, db = client
        db.get_findings_with_explanations.return_value = [
            self._finding(cat="security"),
            self._finding(cat="style"),
        ]
        data = c.get("/v1/runs/1/findings?category=security").json()
        assert data["total"] == 1

    def test_search_filter(self, client):
        c, db = client
        db.get_findings_with_explanations.return_value = [
            {**self._finding(), "message": "eval usage detected", "file_path": "evil.py"},
            {**self._finding(), "message": "clean code", "file_path": "clean.py"},
        ]
        data = c.get("/v1/runs/1/findings?search=eval").json()
        assert data["total"] == 1

    def test_min_confidence_filter(self, client):
        c, db = client
        db.get_findings_with_explanations.return_value = [
            {**self._finding(), "confidence_score": 0.8},
            {**self._finding(), "confidence_score": 0.3},
        ]
        data = c.get("/v1/runs/1/findings?min_confidence=0.5").json()
        assert data["total"] == 1

    def test_group_by_rule(self, client):
        c, db = client
        db.get_findings_with_explanations.return_value = [
            self._finding("SEC-001"),
            self._finding("SEC-001"),
            self._finding("SEC-002"),
        ]
        data = c.get("/v1/runs/1/findings?group_by=rule").json()
        assert data["grouped"] is True
        assert data["total"] == 3
        groups = {g["rule_id"]: g for g in data["groups"]}
        assert groups["SEC-001"]["count"] == 2

    def test_db_confidence_used_over_heuristic(self, client):
        c, db = client
        db.get_findings_with_explanations.return_value = [
            {**self._finding(), "confidence_score": 0.95},
        ]
        data = c.get("/v1/runs/1/findings").json()
        assert data["findings"][0]["confidence"] == 0.95

    def test_empty_run_returns_empty_list(self, client):
        c, db = client
        db.get_findings_with_explanations.return_value = []
        data = c.get("/v1/runs/1/findings").json()
        assert data["total"] == 0
        assert data["findings"] == []


# ════════════════════════════════════════════════════════════
#  GET /v1/runs/{id}/stats  (was /api/runs/<id>/stats)
# ════════════════════════════════════════════════════════════


class TestGetRunStats:
    def test_success(self, client):
        c, db = client
        db.get_run_summary.return_value = {
            "repo_name": "myrepo",
            "status": "complete",
            "findings_count": 10,
            "high_severity_count": 3,
            "medium_severity_count": 4,
            "low_severity_count": 3,
            "explanations_count": 5,
            "avg_explanation_latency": 200,
            "total_cost": 0.001,
        }
        resp = c.get("/v1/runs/1/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["total_findings"] == 10
        assert data["high"] == 3

    def test_run_not_found_returns_404(self, client):
        c, db = client
        db.get_run_summary.return_value = None
        assert c.get("/v1/runs/999/stats").status_code == 404

    def test_db_error_returns_500(self, client):
        c, db = client
        db.get_run_summary.side_effect = Exception("fail")
        assert c.get("/v1/runs/1/stats").status_code == 500

    def test_null_latency_defaults_to_0(self, client):
        c, db = client
        db.get_run_summary.return_value = {
            "repo_name": "r",
            "status": "ok",
            "findings_count": 0,
            "high_severity_count": 0,
            "medium_severity_count": 0,
            "low_severity_count": 0,
            "explanations_count": 0,
            "avg_explanation_latency": None,
            "total_cost": None,
        }
        data = c.get("/v1/runs/1/stats").json()
        assert data["avg_latency_ms"] == 0.0


# ════════════════════════════════════════════════════════════
#  GET /v1/runs/{id}/compliance  (was /api/runs/<id>/compliance)
# ════════════════════════════════════════════════════════════


class TestGetComplianceReport:
    def test_success(self, client):
        c, _ = client
        mock_data = {
            "owasp_results": {"A01": {"status": "PASS", "finding_count": 0}},
            "security_findings": 0,
            "run_id": 1,
        }
        with patch("scripts.generate_compliance_report.get_compliance_data", return_value=mock_data):
            resp = c.get("/v1/runs/1/compliance")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "owasp_results" in data

    def test_error_returns_500(self, client):
        c, _ = client
        with patch("scripts.generate_compliance_report.get_compliance_data", side_effect=Exception("fail")):
            resp = c.get("/v1/runs/1/compliance")
        assert resp.status_code in (404, 500)


# ════════════════════════════════════════════════════════════
#  GET /v1/runs/{id}/summary  (was /api/runs/<id>/summary)
# ════════════════════════════════════════════════════════════


class TestGetPRSummary:
    def test_returns_markdown_summary(self, client):
        c, db = client
        db.get_recent_runs.return_value = [
            {"id": 1, "repo_name": "myrepo", "status": "complete", "started_at": "2024-01-01"}
        ]
        db.get_findings.return_value = []
        resp = c.get("/v1/runs/1/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "summary_markdown" in data

    def test_run_not_found_returns_404(self, client):
        c, db = client
        db.get_recent_runs.return_value = []
        assert c.get("/v1/runs/999/summary").status_code == 404


# ════════════════════════════════════════════════════════════
#  GET /metrics  (Prometheus — new FastAPI endpoint)
# ════════════════════════════════════════════════════════════


class TestMetricsEndpoint:
    def test_returns_200(self, client):
        c, _ = client
        assert c.get("/metrics").status_code == 200

    def test_returns_text_plain(self, client):
        c, _ = client
        resp = c.get("/metrics")
        assert "text/plain" in resp.headers["content-type"]


# ════════════════════════════════════════════════════════════
#  UI serving — React SPA (when built) or legacy /ui/ fallback
# ════════════════════════════════════════════════════════════


class TestUIServing:
    """Root and SPA-fallback routing. Behaviour depends on whether the React
    build is present (FRONTEND/static/dashboard/index.html); both states valid."""

    def test_root_serves_spa_or_redirects(self, client):
        c, _ = client
        resp = c.get("/", follow_redirects=False)
        if resp.status_code == 200:
            # React build present → SPA shell
            assert "text/html" in resp.headers["content-type"]
            assert 'id="root"' in resp.text
        else:
            # No build → legacy redirect to /ui/index.html
            assert resp.status_code in (302, 307)
            assert "/ui/" in resp.headers["location"]

    def test_unknown_api_path_404s_not_shadowed_by_spa(self, client):
        # The SPA catch-all must never intercept /v1/* — unknown API paths
        # still return a JSON 404, not the HTML shell.
        c, _ = client
        resp = c.get("/v1/this-endpoint-does-not-exist")
        assert resp.status_code == 404
        assert "text/html" not in resp.headers.get("content-type", "")

    def test_docs_still_served(self, client):
        # /docs must survive the catch-all.
        c, _ = client
        assert c.get("/docs").status_code == 200
