"""Unit tests for GET /v1/runs/timeline (v5.0.0 Phase A.1 — Vulnerability Timeline)."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from starlette.testclient import TestClient

from FRONTEND.api.deps import get_current_user, get_db
from FRONTEND.api.main import app as fastapi_app


@pytest.fixture()
def client():
    mock_db = MagicMock()
    mock_user = {"id": 7, "email": "u@acrqa.local", "role": "admin"}
    fastapi_app.dependency_overrides[get_db] = lambda: mock_db
    fastapi_app.dependency_overrides[get_current_user] = lambda: mock_user
    with TestClient(fastapi_app, raise_server_exceptions=False) as c:
        yield c, mock_db
    fastapi_app.dependency_overrides.clear()


def _rows():
    """Three runs (oldest→newest), three rules with varying presence."""
    t = datetime(2026, 5, 1)
    return [
        # Run 100 — t+0
        {
            "rule_id": "SEC-001",
            "canonical_severity": "high",
            "run_id": 100,
            "repo_name": "x",
            "started_at": t,
            "count": 2,
        },
        {
            "rule_id": "STYLE-001",
            "canonical_severity": "low",
            "run_id": 100,
            "repo_name": "x",
            "started_at": t,
            "count": 1,
        },
        # Run 110 — t+1
        {
            "rule_id": "SEC-001",
            "canonical_severity": "high",
            "run_id": 110,
            "repo_name": "x",
            "started_at": t + timedelta(days=1),
            "count": 1,
        },
        {
            "rule_id": "VAR-001",
            "canonical_severity": "medium",
            "run_id": 110,
            "repo_name": "x",
            "started_at": t + timedelta(days=1),
            "count": 3,
        },
        # Run 120 — t+2 (newest) — STYLE-001 resolved; SEC-001 still open; VAR-001 still open
        {
            "rule_id": "SEC-001",
            "canonical_severity": "high",
            "run_id": 120,
            "repo_name": "x",
            "started_at": t + timedelta(days=2),
            "count": 1,
        },
        {
            "rule_id": "VAR-001",
            "canonical_severity": "medium",
            "run_id": 120,
            "repo_name": "x",
            "started_at": t + timedelta(days=2),
            "count": 2,
        },
    ]


class TestRuleTimeline:
    def test_empty_when_no_rows(self, client):
        c, db = client
        db.get_rule_timeline.return_value = []
        r = c.get("/v1/runs/timeline")
        assert r.status_code == 200
        body = r.json()
        assert body == {"runs": [], "rules": []}

    def test_returns_runs_ordered_oldest_first(self, client):
        c, db = client
        db.get_rule_timeline.return_value = _rows()
        body = c.get("/v1/runs/timeline").json()
        run_ids = [r["id"] for r in body["runs"]]
        assert run_ids == [100, 110, 120]

    def test_rules_summary_first_last_present(self, client):
        c, db = client
        db.get_rule_timeline.return_value = _rows()
        body = c.get("/v1/runs/timeline").json()
        rules = {r["rule_id"]: r for r in body["rules"]}
        assert rules["SEC-001"]["first_seen_run_id"] == 100
        assert rules["SEC-001"]["last_seen_run_id"] == 120
        assert rules["SEC-001"]["present_run_ids"] == [100, 110, 120]
        assert rules["SEC-001"]["total_occurrences"] == 4
        assert rules["STYLE-001"]["last_seen_run_id"] == 100
        assert rules["STYLE-001"]["present_run_ids"] == [100]

    def test_open_vs_resolved_status(self, client):
        c, db = client
        db.get_rule_timeline.return_value = _rows()
        body = c.get("/v1/runs/timeline").json()
        rules = {r["rule_id"]: r for r in body["rules"]}
        assert rules["SEC-001"]["current_status"] == "open"
        assert rules["VAR-001"]["current_status"] == "open"
        assert rules["STYLE-001"]["current_status"] == "resolved"

    def test_sort_open_then_severity(self, client):
        c, db = client
        db.get_rule_timeline.return_value = _rows()
        body = c.get("/v1/runs/timeline").json()
        ids = [r["rule_id"] for r in body["rules"]]
        # SEC-001 (open, high) → VAR-001 (open, medium) → STYLE-001 (resolved, low)
        assert ids == ["SEC-001", "VAR-001", "STYLE-001"]

    def test_limit_param_forwarded(self, client):
        c, db = client
        db.get_rule_timeline.return_value = []
        c.get("/v1/runs/timeline?limit=50")
        db.get_rule_timeline.assert_called_with(limit=50, repo_name=None)

    def test_repo_param_forwarded(self, client):
        c, db = client
        db.get_rule_timeline.return_value = []
        c.get("/v1/runs/timeline?repo=flask")
        db.get_rule_timeline.assert_called_with(limit=30, repo_name="flask")

    def test_limit_bounds_rejected(self, client):
        c, _ = client
        assert c.get("/v1/runs/timeline?limit=0").status_code == 422
        assert c.get("/v1/runs/timeline?limit=999").status_code == 422

    def test_severity_takes_highest_observed(self, client):
        c, db = client
        # Same rule seen with low first, then high — final summary should pin to high
        rows = [
            {
                "rule_id": "X",
                "canonical_severity": "low",
                "run_id": 1,
                "repo_name": "r",
                "started_at": datetime(2026, 1, 1),
                "count": 1,
            },
            {
                "rule_id": "X",
                "canonical_severity": "high",
                "run_id": 2,
                "repo_name": "r",
                "started_at": datetime(2026, 1, 2),
                "count": 1,
            },
        ]
        db.get_rule_timeline.return_value = rows
        body = c.get("/v1/runs/timeline").json()
        assert body["rules"][0]["severity"] == "high"
