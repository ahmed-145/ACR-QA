"""
ACR-QA live smoke tests — post-deploy health checks against a running FastAPI server.

Run after `make up` or after a Railway deploy. These tests skip automatically
when the server is not reachable (safe for local dev and PR CI).

Marked `smoke` — included in nightly CI after Railway deploy.

Run:
    pytest TESTS/test_live_smoke.py -m smoke -v
    # or against Railway:
    ACRQA_TEST_URL=https://acr-qa.up.railway.app pytest TESTS/test_live_smoke.py -m smoke -v
"""

import os
import time

import httpx
import pytest

BASE_URL = os.environ.get("ACRQA_TEST_URL", "http://localhost:8000")
TIMEOUT = float(os.environ.get("ACRQA_SMOKE_TIMEOUT", "5"))


def _server_reachable() -> bool:
    try:
        r = httpx.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        return r.status_code == 200
    except Exception:
        return False


pytestmark = pytest.mark.smoke


@pytest.fixture(scope="module", autouse=True)
def require_server():
    if not _server_reachable():
        pytest.skip(f"ACR-QA server not reachable at {BASE_URL} — skipping live smoke tests")


def test_health_endpoint():
    r = httpx.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "healthy"


def test_health_response_under_500ms():
    start = time.perf_counter()
    httpx.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms < 500, f"/health took {elapsed_ms:.0f}ms (>500ms threshold)"


def test_docs_endpoint():
    r = httpx.get(f"{BASE_URL}/docs", timeout=TIMEOUT)
    assert r.status_code == 200


def test_openapi_json_endpoint():
    r = httpx.get(f"{BASE_URL}/openapi.json", timeout=TIMEOUT)
    assert r.status_code == 200
    body = r.json()
    assert body.get("info", {}).get("title") == "ACR-QA API"


def test_metrics_endpoint():
    r = httpx.get(f"{BASE_URL}/metrics", timeout=TIMEOUT)
    assert r.status_code == 200
    assert "http_requests_total" in r.text or "python_gc_objects" in r.text


def test_unauthenticated_runs_returns_401():
    r = httpx.get(f"{BASE_URL}/v1/runs", timeout=TIMEOUT)
    assert r.status_code == 401


def test_unauthenticated_scan_returns_401():
    r = httpx.post(
        f"{BASE_URL}/v1/scans",
        json={"target_dir": "."},
        timeout=TIMEOUT,
    )
    assert r.status_code == 401


def test_login_with_wrong_credentials_returns_401():
    r = httpx.post(
        f"{BASE_URL}/v1/auth/login",
        json={"email": "nobody@example.com", "password": "wrong"},
        timeout=TIMEOUT,
    )
    assert r.status_code in (401, 422)


def test_celery_health_endpoint_exists():
    admin_email = os.environ.get("ACRQA_ADMIN_EMAIL", "admin@acrqa.local")
    admin_password = os.environ.get("ACRQA_ADMIN_PASSWORD", "changeme123!")
    login_r = httpx.post(
        f"{BASE_URL}/v1/auth/login",
        json={"email": admin_email, "password": admin_password},
        timeout=TIMEOUT,
    )
    if login_r.status_code != 200:
        pytest.skip("Could not authenticate — skipping Celery health check")
    token = login_r.json().get("access_token", "")
    r = httpx.get(
        f"{BASE_URL}/v1/celery/health",
        headers={"Authorization": f"Bearer {token}"},
        timeout=TIMEOUT,
    )
    assert r.status_code in (200, 503)


def test_full_login_flow():
    admin_email = os.environ.get("ACRQA_ADMIN_EMAIL", "admin@acrqa.local")
    admin_password = os.environ.get("ACRQA_ADMIN_PASSWORD", "changeme123!")
    r = httpx.post(
        f"{BASE_URL}/v1/auth/login",
        json={"email": admin_email, "password": admin_password},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    token = body["access_token"]
    me_r = httpx.get(
        f"{BASE_URL}/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=TIMEOUT,
    )
    assert me_r.status_code == 200
    assert "email" in me_r.json()
