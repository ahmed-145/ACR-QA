"""Tests for GET /v1/findings/{fid}/history (v5.0.0 Phase A.2)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from starlette.testclient import TestClient

from FRONTEND.api.deps import get_current_user, get_db
from FRONTEND.api.main import app as fastapi_app


@pytest.fixture()
def client():
    mock_db = MagicMock()
    mock_user = {"id": 1, "email": "u@x.local", "role": "member"}
    fastapi_app.dependency_overrides[get_db] = lambda: mock_db
    fastapi_app.dependency_overrides[get_current_user] = lambda: mock_user
    with TestClient(fastapi_app, raise_server_exceptions=False) as c:
        yield c, mock_db
    fastapi_app.dependency_overrides.clear()


_FAKE_HISTORY = {
    "file_path": "app.py",
    "line_number": 5,
    "rule_id": "SECURITY-001",
    "first_seen_commit": {
        "sha": "abc1234",
        "date": "2025-12-01T00:00:00Z",
        "author": "Ahmed",
        "subject": "Initial",
    },
    "first_seen_author": "Ahmed",
    "first_seen_date": "2025-12-01T00:00:00Z",
    "commits_touching": [
        {"sha": "deadbee", "date": "2026-01-01T00:00:00Z", "author": "B", "subject": "Refactor"},
        {"sha": "abc1234", "date": "2025-12-01T00:00:00Z", "author": "Ahmed", "subject": "Initial"},
    ],
    "regression_count": 0,
    "near_fix_commits": [
        {"sha": "deadbee", "date": "2026-01-01T00:00:00Z", "author": "B", "subject": "Refactor"},
    ],
    "bounded_by_max_commits": True,
}


class TestFindingHistoryEndpoint:
    def test_404_when_finding_missing(self, client):
        c, db = client
        db.get_finding_by_id.return_value = None
        r = c.get("/v1/findings/123/history")
        assert r.status_code == 404

    def test_returns_history_shape(self, client):
        c, db = client
        db.get_finding_by_id.return_value = {
            "id": 7,
            "file_path": "app.py",
            "line_number": 5,
            "canonical_rule_id": "SECURITY-001",
        }
        with patch(
            "FRONTEND.api.routers.findings.analyze_finding_history",
            create=True,
            return_value=_FAKE_HISTORY,
        ):
            with patch("CORE.engines.time_travel.analyze_finding_history", return_value=_FAKE_HISTORY):
                r = c.get("/v1/findings/7/history")
        assert r.status_code == 200
        body = r.json()
        assert body["finding_id"] == 7
        assert body["first_seen_author"] == "Ahmed"
        assert len(body["commits_touching"]) == 2
        assert body["regression_count"] == 0
        assert len(body["near_fix_commits"]) == 1
        assert body["bounded_by_max_commits"] is True

    def test_passes_max_commits_param(self, client):
        c, db = client
        db.get_finding_by_id.return_value = {
            "id": 7,
            "file_path": "x.py",
            "line_number": 1,
            "canonical_rule_id": "SEC-002",
        }
        with patch("CORE.engines.time_travel.analyze_finding_history", return_value=_FAKE_HISTORY) as m:
            c.get("/v1/findings/7/history?max_commits=10")
        kwargs = m.call_args.kwargs
        assert kwargs["max_commits"] == 10
        assert kwargs["file_path"] == "x.py"
        assert kwargs["line_number"] == 1

    def test_empty_history_when_not_a_git_repo(self, client, tmp_path: Path):
        c, db = client
        db.get_finding_by_id.return_value = {
            "id": 9,
            "file_path": "nope.py",
            "line_number": 1,
            "canonical_rule_id": "SEC-003",
        }
        empty = {
            "file_path": "nope.py",
            "line_number": 1,
            "rule_id": "SEC-003",
            "first_seen_commit": None,
            "first_seen_author": None,
            "first_seen_date": None,
            "commits_touching": [],
            "regression_count": 0,
            "near_fix_commits": [],
            "bounded_by_max_commits": True,
        }
        with patch("CORE.engines.time_travel.analyze_finding_history", return_value=empty):
            r = c.get("/v1/findings/9/history")
        assert r.status_code == 200
        body = r.json()
        assert body["commits_touching"] == []
        assert body["first_seen_commit"] is None
