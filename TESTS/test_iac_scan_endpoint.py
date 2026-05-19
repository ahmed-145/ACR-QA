"""Tests for POST /v1/scans/iac (v5.0.0 Phase A.2)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from starlette.testclient import TestClient

from FRONTEND.api.deps import get_current_user, get_db
from FRONTEND.api.main import app as fastapi_app

SAMPLES = Path(__file__).parent / "samples" / "iac-issues"


@pytest.fixture()
def client():
    mock_db = MagicMock()
    mock_user = {"id": 1, "email": "u@x.local", "role": "admin"}
    fastapi_app.dependency_overrides[get_db] = lambda: mock_db
    fastapi_app.dependency_overrides[get_current_user] = lambda: mock_user
    with TestClient(fastapi_app, raise_server_exceptions=False) as c:
        yield c
    fastapi_app.dependency_overrides.clear()


class TestIaCScanEndpoint:
    def test_scan_returns_findings_for_sample_dir(self, client):
        # Use a relative path from CWD so the path-escape guard accepts it
        rel = str(SAMPLES.relative_to(Path.cwd()))
        r = client.post("/v1/scans/iac", json={"target_dir": rel})
        assert r.status_code == 200
        body = r.json()
        assert body["total"] > 20
        assert set(body["by_provider"].keys()) >= {"terraform", "kubernetes", "dockerfile"}
        assert set(body["by_severity"].keys()) >= {"high", "medium", "low"}

    def test_scan_summary_counts_match_findings(self, client):
        rel = str(SAMPLES.relative_to(Path.cwd()))
        body = client.post("/v1/scans/iac", json={"target_dir": rel}).json()
        assert sum(body["by_provider"].values()) == body["total"]
        assert sum(body["by_severity"].values()) == body["total"]

    def test_scan_rejects_absolute_path_outside_workspace(self, client):
        r = client.post("/v1/scans/iac", json={"target_dir": "/etc"})
        assert r.status_code == 200
        body = r.json()
        assert "error" in body

    def test_scan_rejects_traversal_path(self, client):
        r = client.post("/v1/scans/iac", json={"target_dir": "../../../../etc"})
        assert r.status_code == 200
        body = r.json()
        assert "error" in body

    def test_scan_empty_dir_returns_zero(self, client, tmp_path: Path):
        # tmp_path will not live inside CWD, so the guard rejects it.
        # Use a relative empty subdir inside CWD instead.
        empty = Path("TESTS/__empty_iac_test_dir__")
        empty.mkdir(exist_ok=True)
        try:
            body = client.post("/v1/scans/iac", json={"target_dir": str(empty)}).json()
            assert body.get("total", 0) == 0
        finally:
            empty.rmdir()

    def test_scan_rejects_non_string_target_dir(self, client):
        r = client.post("/v1/scans/iac", json={"target_dir": 123})
        assert r.status_code == 200
        body = r.json()
        assert "error" in body
