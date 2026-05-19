"""Tests for the Review Bottleneck Analyzer (v5.0.0 Phase A5.5 — Point 4)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from CORE.engines.review_bottleneck import (
    ReviewBottleneckResult,
    _gini,
    _parse_iso,
    analyze,
)
from FRONTEND.api.deps import get_current_user, get_db
from FRONTEND.api.main import app as fastapi_app

# ── Gini coefficient ──────────────────────────────────────────────────────────


class TestGini:
    def test_empty_returns_zero(self):
        assert _gini([]) == 0.0

    def test_all_zeros_returns_zero(self):
        assert _gini([0.0, 0.0, 0.0]) == 0.0

    def test_perfectly_equal(self):
        # Everyone reviews the same number: Gini ≈ 0
        g = _gini([5.0, 5.0, 5.0, 5.0])
        assert g == pytest.approx(0.0, abs=0.01)

    def test_fully_concentrated(self):
        # One person does everything: Gini close to 1
        g = _gini([0.0, 0.0, 0.0, 100.0])
        assert g > 0.7

    def test_single_value(self):
        assert _gini([10.0]) == 0.0


# ── ISO timestamp parsing ─────────────────────────────────────────────────────


class TestParseIso:
    def test_parses_iso_strict(self):
        dt = _parse_iso("2026-05-19T10:30:00+03:00")
        assert dt is not None
        assert dt.year == 2026

    def test_parses_git_format(self):
        dt = _parse_iso("2026-05-19 10:30:00 +0300")
        assert dt is not None

    def test_empty_returns_none(self):
        assert _parse_iso("") is None

    def test_garbage_returns_none(self):
        assert _parse_iso("not-a-date") is None


# ── analyze() with mocked git ─────────────────────────────────────────────────


_COMMIT_BLOCK = """\
~~COMMIT~~
author@example.com
committer@example.com
2026-05-15T09:00:00+00:00
2026-05-15T10:00:00+00:00
Fix SQL injection
~~COMMIT~~END
~~COMMIT~~
dev@example.com
committer@example.com
2026-05-16T08:00:00+00:00
2026-05-16T09:30:00+00:00
Add rate limiter
Reviewed-by: committer@example.com
~~COMMIT~~END"""


def _mock_run(stdout: str, returncode: int = 0):
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = ""
    return m


class TestAnalyze:
    def test_happy_path_returns_result(self):
        with patch("subprocess.run", return_value=_mock_run(_COMMIT_BLOCK)):
            r = analyze(repo_path="/fake/repo", days=30)
        assert isinstance(r, ReviewBottleneckResult)
        assert r.total_commits_analyzed == 2
        assert r.days_analyzed == 30

    def test_review_latency_computed(self):
        with patch("subprocess.run", return_value=_mock_run(_COMMIT_BLOCK)):
            r = analyze(repo_path="/fake/repo", days=30)
        # Both commits have ~1h or ~1.5h delta
        assert r.median_time_to_first_review_hours is not None
        assert r.median_time_to_first_review_hours > 0

    def test_pct_without_comment(self):
        with patch("subprocess.run", return_value=_mock_run(_COMMIT_BLOCK)):
            r = analyze(repo_path="/fake/repo", days=30)
        # 1 of 2 commits has Reviewed-by trailer → 50% without
        assert r.pct_merged_without_comment == pytest.approx(0.5, abs=0.01)

    def test_no_commits_returns_zero_result(self):
        with patch("subprocess.run", return_value=_mock_run("", returncode=0)):
            r = analyze(repo_path="/fake/repo", days=30)
        assert r.total_commits_analyzed == 0
        assert r.median_time_to_first_review_hours is None
        assert r.reviewer_load_gini == 0.0

    def test_git_failure_returns_zero_result(self):
        with patch("subprocess.run", return_value=_mock_run("", returncode=128)):
            r = analyze(repo_path="/fake/repo", days=30)
        assert r.total_commits_analyzed == 0

    def test_subprocess_oserror_returns_zero_result(self):
        with patch("subprocess.run", side_effect=OSError("git not found")):
            r = analyze(repo_path="/fake/repo", days=30)
        assert r.total_commits_analyzed == 0

    def test_stale_count_threshold(self):
        # Craft a commit with >168h (7 days) delta
        stale_block = (
            "~~COMMIT~~\na@b.com\nc@b.com\n"
            "2026-05-01T00:00:00+00:00\n"
            "2026-05-10T00:00:00+00:00\n"  # 9 days later
            "Old PR\n~~COMMIT~~END"
        )
        with patch("subprocess.run", return_value=_mock_run(stale_block)):
            r = analyze(repo_path="/fake/repo", days=30)
        assert r.stale_pr_count == 1

    def test_to_dict_shape(self):
        with patch("subprocess.run", return_value=_mock_run(_COMMIT_BLOCK)):
            r = analyze(repo_path="/fake/repo", days=30)
        d = r.to_dict()
        assert set(d.keys()) >= {
            "median_time_to_first_review_hours",
            "reviewer_load_gini",
            "pct_merged_without_comment",
            "top3_reviewer_share",
            "stale_pr_count",
            "total_commits_analyzed",
            "days_analyzed",
            "repo_path",
        }


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
    def test_404_when_run_missing(self, client):
        c, db = client
        db.get_analysis_run.return_value = None
        r = c.get("/v1/runs/999/review-bottleneck")
        assert r.status_code == 404

    def test_200_with_valid_run(self, client):
        c, db = client
        db.get_analysis_run.return_value = {"id": 1, "repo_name": "test-repo"}
        with patch("subprocess.run", return_value=_mock_run(_COMMIT_BLOCK)):
            r = c.get("/v1/runs/1/review-bottleneck?days=30")
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert body["run_id"] == 1
        assert body["repo_name"] == "test-repo"
        assert "total_commits_analyzed" in body

    def test_days_param_forwarded(self, client):
        c, db = client
        db.get_analysis_run.return_value = {"id": 1, "repo_name": "repo"}
        with patch("subprocess.run", return_value=_mock_run(_COMMIT_BLOCK)) as mock_sp:
            r = c.get("/v1/runs/1/review-bottleneck?days=7")
        assert r.status_code == 200
        # Verify git was called with correct --since arg
        call_args = mock_sp.call_args[0][0]
        assert "--since=7 days ago" in call_args

    def test_repo_name_in_response(self, client):
        c, db = client
        db.get_analysis_run.return_value = {"id": 5, "repo_name": "my-project"}
        with patch("subprocess.run", return_value=_mock_run("")):
            r = c.get("/v1/runs/5/review-bottleneck")
        assert r.status_code == 200
        assert r.json()["repo_name"] == "my-project"
