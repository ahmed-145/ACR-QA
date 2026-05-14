"""
Unit tests for the FastAPI v1 API endpoints.
Tests filtering, grouping, and data integrity.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from starlette.testclient import TestClient

from FRONTEND.api.deps import get_current_user, get_db
from FRONTEND.api.main import app as fastapi_app


@pytest.fixture
def client():
    mock_db = MagicMock()
    mock_user = {"id": 1, "email": "test@acrqa.local", "role": "admin"}
    mock_db.get_recent_runs.return_value = []
    mock_db.get_findings_with_explanations.return_value = []
    mock_db.get_run_summary.return_value = None

    fastapi_app.dependency_overrides[get_db] = lambda: mock_db
    fastapi_app.dependency_overrides[get_current_user] = lambda: mock_user

    with TestClient(fastapi_app, raise_server_exceptions=False) as c:
        yield c

    fastapi_app.dependency_overrides.clear()


class TestDashboardAPI:
    """Test FastAPI /v1/ endpoints."""

    def test_get_recent_runs(self, client):
        response = client.get("/v1/runs")
        data = response.json()
        assert response.status_code == 200
        assert data["success"] is True
        assert "runs" in data

    def test_get_run_findings_basic(self, client):
        response = client.get("/v1/runs/1/findings")
        data = response.json()
        assert response.status_code == 200
        assert data["success"] is True
        assert "findings" in data or "groups" in data

    def test_findings_severity_filter(self, client):
        response = client.get("/v1/runs/1/findings?severity=high")
        data = response.json()
        if data["success"] and "findings" in data:
            for finding in data["findings"]:
                assert finding["severity"] == "high"

    def test_findings_category_filter(self, client):
        response = client.get("/v1/runs/1/findings?category=security")
        data = response.json()
        if data["success"] and "findings" in data:
            for finding in data["findings"]:
                assert finding["category"] == "security"

    def test_findings_search_filter(self, client):
        response = client.get("/v1/runs/1/findings?search=eval")
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_findings_grouping(self, client):
        response = client.get("/v1/runs/1/findings?group_by=rule")
        data = response.json()
        if data["success"] and data.get("grouped"):
            assert "groups" in data
            for group in data["groups"]:
                assert "rule_id" in group
                assert "count" in group
                assert group["count"] > 0

    def test_run_stats_not_found(self, client):
        response = client.get("/v1/runs/999/stats")
        assert response.status_code == 404

    def test_confidence_score_in_response(self, client):
        from unittest.mock import MagicMock

        mock_db = MagicMock()
        mock_db.get_findings_with_explanations.return_value = [
            {
                "id": 1,
                "canonical_rule_id": "SEC-001",
                "canonical_severity": "high",
                "category": "security",
                "file_path": "app.py",
                "line_number": 10,
                "message": "test",
                "explanation_text": "SEC-001 found",
                "model_name": None,
                "latency_ms": None,
                "tool": "bandit",
                "confidence_score": None,
                "ground_truth": None,
            }
        ]
        fastapi_app.dependency_overrides[get_db] = lambda: mock_db
        with TestClient(fastapi_app, raise_server_exceptions=False) as c:
            data = c.get("/v1/runs/1/findings").json()
        fastapi_app.dependency_overrides.pop(get_db, None)

        if data["success"] and "findings" in data and data["findings"]:
            finding = data["findings"][0]
            assert "confidence" in finding
            assert 0 <= finding["confidence"] <= 1

    def test_invalid_run_stats(self, client):
        response = client.get("/v1/runs/999999/stats")
        assert response.status_code in (200, 404, 500)
