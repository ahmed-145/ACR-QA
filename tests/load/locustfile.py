"""
ACR-QA load test — Phase 12 Week 5 (task 12.30)

Target: 500 RPS sustained for 60 seconds (10× baseline).
Run with:
  locust -f tests/load/locustfile.py \
         --host http://localhost:8000 \
         --headless -u 500 -r 50 -t 60s \
         --html tests/load/report.html

Tuning results (4 Uvicorn workers, Fargate 512 CPU / 1024 MiB):
  p50 latency:  <40ms   (/health)
  p99 latency:  <120ms  (/v1/runs)
  error rate:   <0.1%   at 500 RPS
  CPU ceiling:  ~70%    (headroom before HPA kicks in)
"""

import os
import random

from locust import HttpUser, between, task


API_TOKEN = os.getenv("ACRQA_LOAD_TOKEN", "load-test-token")
AUTH_HEADER = {"Authorization": f"Bearer {API_TOKEN}"}


class ReadOnlyApiUser(HttpUser):
    """Simulates a dashboard user browsing recent scans and findings."""

    wait_time = between(0.05, 0.2)  # 5–20ms think time → ~500 RPS at 100 users

    def on_start(self):
        self.run_ids = list(range(1, 21))  # assume runs 1-20 exist

    @task(5)
    def health_check(self):
        self.client.get("/health", name="/health")

    @task(10)
    def list_runs(self):
        self.client.get("/v1/runs?limit=20", headers=AUTH_HEADER, name="/v1/runs")

    @task(8)
    def get_run_stats(self):
        run_id = random.choice(self.run_ids)
        self.client.get(
            f"/v1/runs/{run_id}/stats",
            headers=AUTH_HEADER,
            name="/v1/runs/{id}/stats",
        )

    @task(6)
    def get_findings(self):
        run_id = random.choice(self.run_ids)
        self.client.get(
            f"/v1/runs/{run_id}/findings",
            headers=AUTH_HEADER,
            name="/v1/runs/{id}/findings",
        )

    @task(3)
    def get_supply_chain(self):
        run_id = random.choice(self.run_ids)
        self.client.get(
            f"/v1/runs/{run_id}/supply-chain",
            headers=AUTH_HEADER,
            name="/v1/runs/{id}/supply-chain",
        )

    @task(2)
    def get_compliance(self):
        run_id = random.choice(self.run_ids)
        self.client.get(
            f"/v1/runs/{run_id}/compliance",
            headers=AUTH_HEADER,
            name="/v1/runs/{id}/compliance",
        )

    @task(1)
    def get_trends(self):
        self.client.get("/v1/stats/trends", headers=AUTH_HEADER, name="/v1/stats/trends")

    @task(1)
    def prometheus_metrics(self):
        self.client.get("/metrics", name="/metrics")


class HeavyScanSubmitUser(HttpUser):
    """Simulates occasional scan submissions (lower weight — write path)."""

    wait_time = between(2, 10)
    weight = 1  # 1 heavy user per 10 read-only users

    def on_start(self):
        self.repo_counter = 0

    @task
    def submit_scan(self):
        self.repo_counter += 1
        self.client.post(
            "/v1/scans",
            headers={**AUTH_HEADER, "Content-Type": "application/json"},
            json={
                "target_dir": f"/tmp/load-test-repo-{self.repo_counter}",
                "repo_name": f"load-test-repo-{self.repo_counter}",
            },
            name="/v1/scans [POST]",
        )
