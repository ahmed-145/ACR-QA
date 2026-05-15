"""
ACR-QA Locust Load Test
========================
Target:  FastAPI at :8000  (v1 endpoints)
Goal:    50 RPS sustained, p95 < 500ms, error rate < 1%

Run (quick smoke):
    locust -f TESTS/load/locustfile.py --headless -u 10 -r 2 -t 60s \
           --host http://localhost:8000

Run (full 50 RPS):
    locust -f TESTS/load/locustfile.py --headless -u 50 -r 5 -t 120s \
           --host http://localhost:8000 \
           --html DATA/outputs/locust_report.html \
           --csv DATA/outputs/locust

Install:
    pip install locust
"""

import os
import random

from locust import HttpUser, between, task

ADMIN_EMAIL = os.environ.get("ACRQA_ADMIN_EMAIL", "admin@acrqa.local")
ADMIN_PASSWORD = os.environ.get("ACRQA_ADMIN_PASSWORD", "changeme123!")

_token_cache: dict = {}


def _get_token(client) -> str:
    """Authenticate once per user instance and cache the JWT."""
    if "token" not in _token_cache:
        r = client.post(
            "/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            name="/v1/auth/login [setup]",
        )
        if r.status_code == 200:
            _token_cache["token"] = r.json().get("access_token", "")
        else:
            _token_cache["token"] = ""
    return _token_cache["token"]


class ReadOnlyUser(HttpUser):
    """
    Simulates a dashboard user reading scan results.
    Heaviest load profile — 70% of users.
    """

    wait_time = between(0.5, 2.0)
    weight = 70

    def on_start(self):
        self.token = _get_token(self.client)
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self._run_ids: list[int] = []
        self._prefetch_runs()

    def _prefetch_runs(self):
        r = self.client.get(
            "/v1/runs?limit=10",
            headers=self.headers,
            name="/v1/runs [prefetch]",
        )
        if r.status_code == 200:
            body = r.json()
            runs = body if isinstance(body, list) else body.get("runs", [])
            self._run_ids = [run["id"] for run in runs[:10]]

    @task(5)
    def list_runs(self):
        self.client.get("/v1/runs?limit=20", headers=self.headers, name="/v1/runs")

    @task(3)
    def get_run_detail(self):
        if not self._run_ids:
            return
        run_id = random.choice(self._run_ids)
        self.client.get(
            f"/v1/runs/{run_id}/findings",
            headers=self.headers,
            name="/v1/runs/{id}/findings",
        )

    @task(2)
    def get_run_stats(self):
        if not self._run_ids:
            return
        run_id = random.choice(self._run_ids)
        self.client.get(
            f"/v1/runs/{run_id}/stats",
            headers=self.headers,
            name="/v1/runs/{id}/stats",
        )

    @task(2)
    def get_supply_chain(self):
        if not self._run_ids:
            return
        run_id = random.choice(self._run_ids)
        self.client.get(
            f"/v1/runs/{run_id}/supply-chain",
            headers=self.headers,
            name="/v1/runs/{id}/supply-chain",
        )

    @task(1)
    def health_check(self):
        self.client.get("/health", name="/health")

    @task(1)
    def get_me(self):
        self.client.get("/v1/auth/me", headers=self.headers, name="/v1/auth/me")


class ScanSubmitUser(HttpUser):
    """
    Simulates a CI pipeline submitting new scans.
    Low frequency — 30% of users.
    """

    wait_time = between(5.0, 15.0)
    weight = 30

    def on_start(self):
        self.token = _get_token(self.client)
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(3)
    def submit_scan(self):
        payload = {
            "target_dir": random.choice(
                [
                    "TESTS/samples/comprehensive-issues",
                    "TESTS/fixtures",
                    "CORE/",
                ]
            )
        }
        with self.client.post(
            "/v1/scans",
            json=payload,
            headers=self.headers,
            name="/v1/scans",
            catch_response=True,
        ) as r:
            if r.status_code in (202, 404, 422):
                r.success()
            else:
                r.failure(f"Unexpected status {r.status_code}")

    @task(2)
    def poll_scan_status(self):
        r = self.client.get(
            "/v1/scans",
            headers=self.headers,
            name="/v1/scans [list]",
        )
        if r.status_code == 200:
            jobs = r.json() if isinstance(r.json(), list) else []
            if jobs:
                job_id = random.choice(jobs)["id"] if jobs else None
                if job_id:
                    self.client.get(
                        f"/v1/scans/{job_id}",
                        headers=self.headers,
                        name="/v1/scans/{id}",
                    )

    @task(1)
    def list_runs(self):
        self.client.get("/v1/runs?limit=5", headers=self.headers, name="/v1/runs")
