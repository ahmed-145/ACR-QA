"""
God-mode tests for FRONTEND/app.py (target: 50%+)

Uses Flask test client with the global `db` object fully mocked.
Each test class patches `FRONTEND.app.db` to avoid real database.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure FRONTEND is importable
sys.path.insert(0, str(Path(__file__).parent.parent))


# ─────────────────────────────────────────────────────────────
#  App fixture — mock db at module level
# ─────────────────────────────────────────────────────────────


@pytest.fixture()
def mock_db():
    return MagicMock()


@pytest.fixture()
def client(mock_db):
    with patch("DATABASE.database.Database"):
        with patch("CORE.utils.rate_limiter.redis.Redis") as mock_redis_cls:
            mock_redis_cls.return_value.ping.return_value = True
            with patch("CORE.engines.explainer.Groq"):
                from FRONTEND.app import app

                app.config["TESTING"] = True
                with app.test_client() as c:
                    with patch("FRONTEND.app.db", mock_db):
                        yield c, mock_db


# ════════════════════════════════════════════════════════════
#  _calculate_confidence (pure function)
# ════════════════════════════════════════════════════════════


class TestCalculateConfidence:
    def _conf(self, finding):
        with patch("DATABASE.database.Database"):
            with patch("CORE.engines.explainer.Groq"):
                from FRONTEND.app import _calculate_confidence

                return _calculate_confidence(finding)

    def test_baseline_no_extras(self):
        score = self._conf({})
        assert score == 0.5

    def test_rule_cited_adds_02(self):
        score = self._conf(
            {
                "canonical_rule_id": "SEC-001",
                "explanation_text": "This violates SEC-001 because...",
            }
        )
        assert score >= 0.7

    def test_has_explanation_adds_01(self):
        score = self._conf({"explanation_text": "some explanation"})
        assert score >= 0.6

    def test_high_severity_adds_01(self):
        score = self._conf({"canonical_severity": "high"})
        assert score >= 0.6

    def test_security_category_adds_01(self):
        score = self._conf({"category": "security"})
        assert score >= 0.6

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


# ════════════════════════════════════════════════════════════
#  /api/health
# ════════════════════════════════════════════════════════════


class TestHealthEndpoint:
    def test_returns_200(self, client):
        c, _ = client
        resp = c.get("/api/health")
        assert resp.status_code == 200

    def test_returns_healthy(self, client):
        c, _ = client
        data = json.loads(resp := c.get("/api/health").data)
        assert data["status"] == "healthy"

    def test_returns_version(self, client):
        c, _ = client
        data = json.loads(c.get("/api/health").data)
        assert "version" in data


# ════════════════════════════════════════════════════════════
#  /api/runs
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
        resp = c.get("/api/runs")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] is True
        assert len(data["runs"]) == 1
        assert data["runs"][0]["total_findings"] == 5

    def test_db_error_returns_500(self, client):
        c, db = client
        db.get_recent_runs.side_effect = Exception("db down")
        resp = c.get("/api/runs")
        assert resp.status_code == 500
        data = json.loads(resp.data)
        assert data["success"] is False

    def test_custom_limit_param(self, client):
        c, db = client
        db.get_recent_runs.return_value = []
        c.get("/api/runs?limit=5")
        db.get_recent_runs.assert_called_once_with(limit=5)

    def test_no_summary_defaults_to_zero(self, client):
        c, db = client
        db.get_recent_runs.return_value = [
            {"id": 1, "repo_name": "r", "pr_number": None, "status": "complete", "started_at": "2024-01-01"}
        ]
        db.get_run_summary.return_value = None
        resp = c.get("/api/runs")
        data = json.loads(resp.data)
        assert data["runs"][0]["total_findings"] == 0


# ════════════════════════════════════════════════════════════
#  /api/runs/<run_id>/findings
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
        resp = c.get("/api/runs/1/findings")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] is True
        assert data["total"] == 1

    def test_severity_filter(self, client):
        c, db = client
        db.get_findings_with_explanations.return_value = [
            self._finding(sev="high"),
            self._finding(sev="low"),
        ]
        resp = c.get("/api/runs/1/findings?severity=high")
        data = json.loads(resp.data)
        assert data["total"] == 1
        assert data["findings"][0]["severity"] == "high"

    def test_category_filter(self, client):
        c, db = client
        db.get_findings_with_explanations.return_value = [
            self._finding(cat="security"),
            self._finding(cat="style"),
        ]
        resp = c.get("/api/runs/1/findings?category=security")
        data = json.loads(resp.data)
        assert data["total"] == 1

    def test_search_filter(self, client):
        c, db = client
        db.get_findings_with_explanations.return_value = [
            {**self._finding(), "message": "eval usage detected", "file_path": "evil.py"},
            {**self._finding(), "message": "clean code", "file_path": "clean.py"},
        ]
        resp = c.get("/api/runs/1/findings?search=eval")
        data = json.loads(resp.data)
        assert data["total"] == 1

    def test_min_confidence_filter(self, client):
        c, db = client
        db.get_findings_with_explanations.return_value = [
            {**self._finding(), "confidence_score": 0.8},
            {**self._finding(), "confidence_score": 0.3},
        ]
        resp = c.get("/api/runs/1/findings?min_confidence=0.5")
        data = json.loads(resp.data)
        assert data["total"] == 1

    def test_group_by_rule(self, client):
        c, db = client
        db.get_findings_with_explanations.return_value = [
            self._finding("SEC-001"),
            self._finding("SEC-001"),
            self._finding("SEC-002"),
        ]
        resp = c.get("/api/runs/1/findings?group_by=rule")
        data = json.loads(resp.data)
        assert data["grouped"] is True
        assert data["total"] == 3
        groups = {g["rule_id"]: g for g in data["groups"]}
        assert groups["SEC-001"]["count"] == 2

    def test_db_error_returns_500(self, client):
        c, db = client
        db.get_findings_with_explanations.side_effect = Exception("fail")
        resp = c.get("/api/runs/1/findings")
        assert resp.status_code == 500

    def test_db_confidence_used_over_heuristic(self, client):
        c, db = client
        db.get_findings_with_explanations.return_value = [
            {**self._finding(), "confidence_score": 0.95},
        ]
        resp = c.get("/api/runs/1/findings")
        data = json.loads(resp.data)
        assert data["findings"][0]["confidence"] == 0.95


# ════════════════════════════════════════════════════════════
#  /api/runs/<run_id>/stats
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
        resp = c.get("/api/runs/1/stats")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] is True
        assert data["total_findings"] == 10
        assert data["high"] == 3

    def test_run_not_found_returns_404(self, client):
        c, db = client
        db.get_run_summary.return_value = None
        resp = c.get("/api/runs/999/stats")
        assert resp.status_code == 404

    def test_db_error_returns_500(self, client):
        c, db = client
        db.get_run_summary.side_effect = Exception("fail")
        resp = c.get("/api/runs/1/stats")
        assert resp.status_code == 500

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
        resp = c.get("/api/runs/1/stats")
        data = json.loads(resp.data)
        assert data["avg_latency_ms"] == 0.0


# ════════════════════════════════════════════════════════════
#  /api/categories
# ════════════════════════════════════════════════════════════


class TestGetCategories:
    def test_returns_sorted_unique_categories(self, client):
        c, db = client
        db.get_findings.return_value = [
            {"category": "security"},
            {"category": "style"},
            {"category": "security"},
            {"category": "best-practice"},
        ]
        resp = c.get("/api/categories")
        data = json.loads(resp.data)
        assert data["success"] is True
        assert data["categories"] == sorted({"security", "style", "best-practice"})

    def test_db_error_returns_500(self, client):
        c, db = client
        db.get_findings.side_effect = Exception("fail")
        resp = c.get("/api/categories")
        assert resp.status_code == 500

    def test_empty_findings_returns_empty_list(self, client):
        c, db = client
        db.get_findings.return_value = []
        resp = c.get("/api/categories")
        data = json.loads(resp.data)
        assert data["categories"] == []


# ════════════════════════════════════════════════════════════
#  /api/fix-confidence/<rule_id>
# ════════════════════════════════════════════════════════════


class TestGetFixConfidence:
    def test_known_rule_returns_confidence(self, client):
        c, _ = client
        resp = c.get("/api/fix-confidence/IMPORT-001")
        data = json.loads(resp.data)
        assert data["success"] is True
        assert "confidence" in data
        # endpoint returns integer 0-100
        assert 0 < data["confidence"] <= 100

    def test_unknown_rule_returns_fallback(self, client):
        c, _ = client
        resp = c.get("/api/fix-confidence/UNKNOWN-999")
        data = json.loads(resp.data)
        assert data["success"] is True
        # Unknown rules fall back to 50 (manual fix recommended)
        assert data["confidence"] == 50
        assert data["auto_fixable"] is False


# ════════════════════════════════════════════════════════════
#  /api/repos
# ════════════════════════════════════════════════════════════


class TestGetRepos:
    def test_returns_repo_list(self, client):
        c, db = client
        db.get_repos_with_runs.return_value = ["repo-a", "repo-b"]
        resp = c.get("/api/repos")
        data = json.loads(resp.data)
        assert data["success"] is True
        assert "repo-a" in data["repos"]

    def test_db_error_returns_500(self, client):
        c, db = client
        db.get_repos_with_runs.side_effect = Exception("fail")
        resp = c.get("/api/repos")
        assert resp.status_code == 500


# ════════════════════════════════════════════════════════════
#  /api/quick-stats
# ════════════════════════════════════════════════════════════


class TestQuickStats:
    def test_returns_stats(self, client):
        c, db = client
        db.get_recent_runs.return_value = [{"id": 1}]
        db.get_run_summary.return_value = {
            "findings_count": 5,
            "high_severity_count": 1,
            "medium_severity_count": 2,
            "low_severity_count": 2,
            "explanations_count": 1,
            "avg_explanation_latency": 150,
            "total_cost": 0.0005,
        }
        db.get_findings_with_explanations.return_value = []
        resp = c.get("/api/quick-stats")
        data = json.loads(resp.data)
        assert data["success"] is True
        assert "stats" in data

    def test_no_runs_returns_zeros(self, client):
        c, db = client
        db.get_recent_runs.return_value = []
        resp = c.get("/api/quick-stats")
        data = json.loads(resp.data)
        assert data["success"] is True


# ════════════════════════════════════════════════════════════
#  /api/analyze (POST)
# ════════════════════════════════════════════════════════════


class TestAnalyzeSingleFile:
    def test_no_content_returns_400(self, client):
        c, _ = client
        resp = c.post("/api/analyze", data=json.dumps({}), content_type="application/json")
        assert resp.status_code == 400

    def test_with_content_calls_ruff(self, client):
        c, _ = client
        mock_result = MagicMock()
        mock_result.stdout = "[]"
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result):
            resp = c.post(
                "/api/analyze",
                data=json.dumps({"content": "x = 1\n", "filename": "test.py"}),
                content_type="application/json",
            )
        data = json.loads(resp.data)
        assert data["success"] is True
        assert "findings" in data

    def test_ruff_findings_included(self, client):
        c, _ = client
        ruff_output = json.dumps(
            [
                {
                    "location": {"row": 1, "column": 1},
                    "code": "F401",
                    "message": "unused import",
                }
            ]
        )
        mock_result = MagicMock()
        mock_result.stdout = ruff_output
        mock_result.returncode = 1
        with patch("subprocess.run", return_value=mock_result):
            resp = c.post(
                "/api/analyze",
                data=json.dumps({"content": "import os\n", "filename": "test.py"}),
                content_type="application/json",
            )
        data = json.loads(resp.data)
        assert data["success"] is True
        # Ruff findings should appear
        ruff_findings = [f for f in data["findings"] if f.get("tool") == "ruff"]
        assert len(ruff_findings) >= 1


# ════════════════════════════════════════════════════════════
#  /api/runs/<run_id>/compliance
# ════════════════════════════════════════════════════════════


class TestGetComplianceReport:
    def test_success(self, client):
        c, db = client
        mock_data = {
            "owasp_results": {"A01": {"status": "PASS", "finding_count": 0}},
            "security_findings": 0,
            "run_id": 1,
        }
        with patch("scripts.generate_compliance_report.get_compliance_data", return_value=mock_data):
            resp = c.get("/api/runs/1/compliance")
        data = json.loads(resp.data)
        assert data["success"] is True
        assert "owasp_results" in data

    def test_db_error_returns_500(self, client):
        c, db = client
        with patch("scripts.generate_compliance_report.get_compliance_data", side_effect=Exception("fail")):
            resp = c.get("/api/runs/1/compliance")
        assert resp.status_code == 500


# ════════════════════════════════════════════════════════════
#  /api/policy
# ════════════════════════════════════════════════════════════


class TestGetPolicyConfig:
    def test_returns_policy_dict(self, client):
        c, _ = client
        resp = c.get("/api/policy")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] is True
        # Key is active_policy not policy
        assert "active_policy" in data


# ════════════════════════════════════════════════════════════
#  /api/runs/<run_id>/summary
# ════════════════════════════════════════════════════════════


class TestGetPRSummary:
    def test_returns_markdown_summary(self, client):
        c, db = client
        db.get_recent_runs.return_value = [
            {"id": 1, "repo_name": "myrepo", "status": "complete", "started_at": "2024-01-01"}
        ]
        db.get_findings.return_value = []
        resp = c.get("/api/runs/1/summary")
        data = json.loads(resp.data)
        assert data["success"] is True
        assert "summary_markdown" in data

    def test_run_not_found_returns_404(self, client):
        c, db = client
        db.get_recent_runs.return_value = []  # run 999 not in list
        resp = c.get("/api/runs/999/summary")
        assert resp.status_code == 404


# ════════════════════════════════════════════════════════════
#  /api/findings/<finding_id>/feedback (POST)
# ════════════════════════════════════════════════════════════


class TestSubmitFeedback:
    def test_valid_feedback_accepted(self, client):
        c, db = client
        # db.execute finds the finding, db.insert_feedback returns an id
        db.execute.return_value = [{"id": 1}]
        db.insert_feedback.return_value = 42
        resp = c.post(
            "/api/findings/1/feedback",
            data=json.dumps({"is_helpful": True, "comment": "good"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] is True
        assert data["feedback_id"] == 42

    def test_db_error_returns_500(self, client):
        c, db = client
        db.execute.side_effect = Exception("db fail")
        resp = c.post(
            "/api/findings/1/feedback",
            data=json.dumps({"is_helpful": True}),
            content_type="application/json",
        )
        assert resp.status_code == 500

    def test_finding_not_found_returns_404(self, client):
        c, db = client
        db.execute.return_value = []  # empty → not found
        resp = c.post(
            "/api/findings/999/feedback",
            data=json.dumps({"is_helpful": True}),
            content_type="application/json",
        )
        assert resp.status_code == 404


# ════════════════════════════════════════════════════════════
#  /api/findings/<id>/mark-false-positive (POST)
# ════════════════════════════════════════════════════════════


class TestMarkFalsePositive:
    def test_marks_finding(self, client):
        c, db = client
        db.execute.return_value = [{"id": 1}]
        db.insert_feedback.return_value = 10
        resp = c.post(
            "/api/findings/1/mark-false-positive",
            data=json.dumps({"reason": "test"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] is True

    def test_finding_not_found_returns_404(self, client):
        c, db = client
        db.execute.return_value = []  # not found
        resp = c.post(
            "/api/findings/999/mark-false-positive",
            data=json.dumps({"reason": "test"}),
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_db_execute_error_returns_500(self, client):
        c, db = client
        db.execute.side_effect = Exception("crash")
        resp = c.post(
            "/api/findings/1/mark-false-positive",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 500
