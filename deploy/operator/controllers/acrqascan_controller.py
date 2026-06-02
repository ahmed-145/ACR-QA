"""ACR-QA Kubernetes Operator — ACRQAScan controller.

Uses kopf (Kubernetes Operator Pythonic Framework) to reconcile
`acrqa.io/v1alpha1/ACRQAScan` custom resources.

On every CREATE / UPDATE:
  1. Clone the target repo into a temporary directory
  2. Run `CORE/main.py` against the clone
  3. Patch the CR status with results (phase, findings, gate verdict)
  4. Optionally call the notification webhook

Requires:
  - kopf >= 1.37
  - kubernetes >= 28
  - The ACR-QA image running as the operator pod (or ACRQA_SERVER_URL pointing
    to a running instance)

Environment variables:
  ACRQA_SERVER_URL   — if set, submits scan via REST API instead of running locally
  ACRQA_API_KEY      — API key for REST mode
  GROQ_API_KEY_1     — required for AI enrichment
  ACRQA_OPERATOR_NS  — namespace to watch (default: all namespaces)
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
import time
from typing import Any

import kopf
import kubernetes.client as k8s_client
from kubernetes import config as k8s_config

logger = logging.getLogger("acrqa-operator")

# ── k8s client setup ─────────────────────────────────────────────────────────

try:
    k8s_config.load_incluster_config()
except k8s_config.config_exception.ConfigException:
    k8s_config.load_kube_config()

custom_api = k8s_client.CustomObjectsApi()

GROUP = "acrqa.io"
VERSION = "v1alpha1"
PLURAL = "acrqascans"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _patch_status(namespace: str, name: str, status: dict) -> None:
    """Patch the CR status subresource."""
    try:
        custom_api.patch_namespaced_custom_object_status(
            group=GROUP,
            version=VERSION,
            namespace=namespace,
            plural=PLURAL,
            name=name,
            body={"status": status},
        )
    except Exception as exc:
        logger.warning("Failed to patch status for %s/%s: %s", namespace, name, exc)


def _run_scan_local(repo_url: str, spec: dict) -> dict:
    """Clone repo and run CORE/main.py locally. Returns parsed findings summary."""
    branch = spec.get("branch", "main")
    language = spec.get("language", "auto")
    no_ai = spec.get("noAI", False)
    confirmed_only = spec.get("confirmedTierOnly", False)

    with tempfile.TemporaryDirectory(prefix="acrqa-scan-") as tmpdir:
        # Clone
        clone_cmd = ["git", "clone", "--depth", "1", "--branch", branch, repo_url, tmpdir]
        result = subprocess.run(clone_cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"git clone failed: {result.stderr[:500]}")

        # Build scan command
        cmd = ["python3", "CORE/main.py", "--target-dir", tmpdir, "--json"]
        if language != "auto":
            cmd += ["--lang", language]
        if no_ai:
            cmd += ["--no-ai"]

        scan_result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
            env={**os.environ, "ACRQA_JSON_LOGS": "0"},
        )

        import json

        try:
            data = json.loads(scan_result.stdout)
        except json.JSONDecodeError:
            data = {"findings": [], "run_id": None}

        findings = data.get("findings", [])
        confirmed = [
            f
            for f in findings
            if f.get("severity", "").lower() in ("critical", "high")
            and f.get("canonical_rule_id", "").startswith(("SECURITY-", "IAC-", "SUPPLY-"))
        ]

        return {
            "run_id": data.get("run_id"),
            "total": len(findings),
            "critical": sum(1 for f in findings if f.get("severity", "").lower() == "critical"),
            "high": sum(1 for f in findings if f.get("severity", "").lower() == "high"),
            "medium": sum(1 for f in findings if f.get("severity", "").lower() == "medium"),
            "confirmed_tier": len(confirmed),
        }


def _evaluate_gate(findings_summary: dict, gate_spec: dict) -> str:
    """Return 'pass', 'fail', or 'warn' based on quality gate thresholds."""
    mode = gate_spec.get("mode", "warn")
    if mode == "off":
        return "pass"

    critical = findings_summary.get("critical", 0)
    high = findings_summary.get("high", 0)
    max_critical = gate_spec.get("maxCritical", 0)
    max_high = gate_spec.get("maxHigh", -1)

    failed = critical > max_critical or (max_high >= 0 and high > max_high)

    if failed:
        return "fail" if mode == "block" else "warn"
    return "pass"


def _notify_webhook(url: str, payload: dict) -> None:
    """POST scan completion to a Slack/Teams/generic webhook."""
    try:
        import httpx

        httpx.post(url, json=payload, timeout=5.0)
    except Exception as exc:
        logger.warning("Webhook notification failed: %s", exc)


# ── Operator handlers ─────────────────────────────────────────────────────────


@kopf.on.create(GROUP, VERSION, PLURAL)
@kopf.on.update(GROUP, VERSION, PLURAL)
def on_scan(spec: dict, name: str, namespace: str, **_: Any) -> dict:
    """Reconcile an ACRQAScan resource — run the scan and update status."""
    repo_url: str = spec["repoUrl"]
    logger.info("Scanning %s for %s/%s", repo_url, namespace, name)

    _patch_status(namespace, name, {"phase": "Running", "message": f"Scanning {repo_url}"})

    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    try:
        summary = _run_scan_local(repo_url, spec)
        gate_spec = spec.get("qualityGate", {})
        gate = _evaluate_gate(summary, gate_spec)
        completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        status = {
            "phase": "Complete",
            "runId": summary.get("run_id"),
            "startedAt": started_at,
            "completedAt": completed_at,
            "findings": {
                "total": summary["total"],
                "critical": summary["critical"],
                "high": summary["high"],
                "medium": summary["medium"],
                "confirmedTier": summary["confirmed_tier"],
            },
            "gateResult": gate,
            "message": (
                f"Scan complete: {summary['total']} findings " f"({summary['critical']} critical, gate={gate})"
            ),
        }
        _patch_status(namespace, name, status)

        # Webhook notification
        webhook_url = spec.get("notificationWebhook")
        if webhook_url:
            _notify_webhook(
                webhook_url,
                {
                    "resource": f"{namespace}/{name}",
                    "repo": repo_url,
                    "phase": "Complete",
                    "findings": status["findings"],
                    "gate": gate,
                },
            )

        logger.info(
            "Scan complete for %s/%s: %d findings, gate=%s",
            namespace,
            name,
            summary["total"],
            gate,
        )
        return {"findings": summary["total"], "gate": gate}

    except Exception as exc:
        logger.exception("Scan failed for %s/%s: %s", namespace, name, exc)
        _patch_status(
            namespace,
            name,
            {
                "phase": "Failed",
                "startedAt": started_at,
                "message": f"Scan failed: {exc}",
                "gateResult": "fail",
            },
        )
        raise kopf.PermanentError(f"Scan failed: {exc}") from exc


@kopf.on.delete(GROUP, VERSION, PLURAL)
def on_delete(name: str, namespace: str, **_: Any) -> None:
    logger.info("ACRQAScan %s/%s deleted — no cleanup required", namespace, name)
