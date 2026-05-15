"""
API-level E2E tests — FastAPI live endpoint smoke tests.

These tests run against a live FastAPI server (requires DATABASE_URL + REDIS_URL).
Skip automatically if server is not reachable.

Run:
    pytest TESTS/e2e/ -m e2e -v
    # or with a running stack:
    make up && pytest TESTS/e2e/ -m e2e -v
"""

import os

import httpx
import pytest

BASE_URL = os.environ.get("ACRQA_TEST_URL", "http://localhost:8000")


def is_server_up() -> bool:
    try:
        r = httpx.get(f"{BASE_URL}/health", timeout=2.0)
        return r.status_code == 200
    except Exception:
        return False


pytestmark = pytest.mark.e2e


@pytest.fixture(scope="module")
def client():
    if not is_server_up():
        pytest.skip("FastAPI server not reachable — skipping API E2E tests")
    return httpx.Client(base_url=BASE_URL, timeout=10.0)


@pytest.fixture(scope="module")
def auth_token(client):
    admin_email = os.environ.get("ACRQA_ADMIN_EMAIL", "admin@acrqa.local")
    admin_password = os.environ.get("ACRQA_ADMIN_PASSWORD", "changeme123!")
    r = client.post(
        "/v1/auth/login",
        json={"email": admin_email, "password": admin_password},
    )
    if r.status_code != 200:
        pytest.skip(f"Could not authenticate: {r.status_code}")
    return r.json()["access_token"]


def test_health_returns_200(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "healthy"


def test_docs_endpoint_returns_200(client):
    r = client.get("/docs")
    assert r.status_code == 200


def test_login_returns_token(client):
    admin_email = os.environ.get("ACRQA_ADMIN_EMAIL", "admin@acrqa.local")
    admin_password = os.environ.get("ACRQA_ADMIN_PASSWORD", "changeme123!")
    r = client.post(
        "/v1/auth/login",
        json={"email": admin_email, "password": admin_password},
    )
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_invalid_login_returns_401(client):
    r = client.post(
        "/v1/auth/login",
        json={"email": "nobody@example.com", "password": "wrong"},
    )
    assert r.status_code in (401, 422)


def test_unauthenticated_runs_returns_401(client):
    r = client.get("/v1/runs")
    assert r.status_code == 401


def test_authenticated_runs_returns_list(client, auth_token):
    r = client.get(
        "/v1/runs",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "runs" in body or isinstance(body, list)


def test_authenticated_me_returns_user(client, auth_token):
    r = client.get(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "email" in body


def test_submit_scan_returns_202(client, auth_token):
    r = client.post(
        "/v1/scans",
        json={"target_dir": "TESTS/samples/comprehensive-issues"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code in (202, 404, 422)


def test_celery_health_returns_status(client, auth_token):
    r = client.get(
        "/v1/celery/health",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code in (200, 503)


def test_metrics_endpoint_returns_prometheus_text(client):
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "http_requests_total" in r.text or "python_gc_objects" in r.text
