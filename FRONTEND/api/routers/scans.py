"""Scans router — async scan dispatch via Celery, single-file analysis, quick refresh."""

from __future__ import annotations

import asyncio
import json as json_module
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, status

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from FRONTEND.api.deps import get_current_user
from FRONTEND.api.models import (
    AIDetectRequest,
    AnalyzeFileRequest,
    RefreshFindingsRequest,
    ScanJobOut,
    ScanRequest,
    SCAScanRequest,
    SecretsScanRequest,
)

router = APIRouter(prefix="/scans", tags=["scans"])


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ScanJobOut,
    summary="Queue a full repository scan (async)",
)
async def create_scan(body: ScanRequest, user: dict = Depends(get_current_user)):
    """Enqueue an analysis job and return a job_id immediately.
    Poll GET /v1/scans/{job_id} for status.
    """
    from CORE.tasks import run_analysis_task

    task = run_analysis_task.delay(
        target_dir=body.target_dir,
        repo_name=body.repo_name,
        pr_number=body.pr_number,
        limit=body.limit,
    )
    return ScanJobOut(job_id=task.id, status="queued")


@router.get("/{job_id}", response_model=ScanJobOut, summary="Poll scan job status")
async def get_scan_status(job_id: str, user: dict = Depends(get_current_user)):
    """Returns queued | started | completed | failed with result when done."""
    from CORE.tasks import celery_app

    ar = celery_app.AsyncResult(job_id)

    # Celery state → our status vocabulary
    state_map = {
        "PENDING": "queued",
        "STARTED": "started",
        "SUCCESS": "completed",
        "FAILURE": "failed",
        "RETRY": "started",
        "REVOKED": "failed",
    }
    our_status = state_map.get(ar.state, ar.state.lower())

    result = None
    if ar.ready():
        try:
            result = ar.result if ar.successful() else {"error": str(ar.result)}
        except Exception:
            result = {"error": "Could not retrieve result"}

    return ScanJobOut(job_id=job_id, status=our_status, result=result)


@router.post("/analyze", summary="Analyze a single file snippet (sync, no DB write)")
async def analyze_file(body: AnalyzeFileRequest, user: dict = Depends(get_current_user)):
    """Run Ruff + Vulture + Bandit on a code snippet and return findings inline."""
    findings: list[dict] = []

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(body.content)
        temp_path = f.name

    try:
        # Ruff
        r = await asyncio.to_thread(
            subprocess.run,
            ["ruff", "check", temp_path, "--output-format=json"],
            capture_output=True,
            text=True,
        )
        if r.stdout:
            for item in json_module.loads(r.stdout):
                findings.append(
                    {
                        "line": item.get("location", {}).get("row", 1),
                        "column": item.get("location", {}).get("column", 1),
                        "rule_id": item.get("code", "UNKNOWN"),
                        "severity": "medium" if (item.get("code", "")).startswith("E") else "low",
                        "message": item.get("message", ""),
                        "tool": "ruff",
                    }
                )

        # Vulture
        r = await asyncio.to_thread(
            subprocess.run,
            ["vulture", temp_path, "--min-confidence", "80"],
            capture_output=True,
            text=True,
        )
        for line in r.stdout.strip().split("\n"):
            if line and ":" in line:
                parts = line.split(":")
                if len(parts) >= 3:
                    findings.append(
                        {
                            "line": int(parts[1]) if parts[1].isdigit() else 1,
                            "column": 1,
                            "rule_id": "DEAD-001",
                            "severity": "low",
                            "message": ":".join(parts[2:]).strip(),
                            "tool": "vulture",
                        }
                    )

        # Bandit
        try:
            r = await asyncio.to_thread(
                subprocess.run,
                ["bandit", "-f", "json", "-q", temp_path],
                capture_output=True,
                text=True,
            )
            if r.stdout:
                for issue in json_module.loads(r.stdout).get("results", []):
                    sev = issue.get("issue_severity", "LOW").lower()
                    findings.append(
                        {
                            "line": issue.get("line_number", 1),
                            "column": 1,
                            "rule_id": issue.get("test_id", "B000"),
                            "severity": "high" if sev == "high" else "medium" if sev == "medium" else "low",
                            "message": issue.get("issue_text", ""),
                            "tool": "bandit",
                            "category": "security",
                        }
                    )
        except Exception:
            pass
    finally:
        os.unlink(temp_path)

    return {"success": True, "filename": body.filename, "findings": findings, "total": len(findings)}


@router.post("/refresh", summary="Re-run detection tools and sync DB (no AI explanations)")
async def refresh_findings(body: RefreshFindingsRequest, user: dict = Depends(get_current_user)):
    """Quick refresh: run tools → normalize → store findings without LLM calls."""
    from CORE.engines.normalizer import normalize_all
    from DATABASE.database import Database

    db = Database()
    project_root = Path(__file__).parent.parent.parent.parent

    if not body.skip_detection:
        await asyncio.to_thread(
            subprocess.run,
            ["bash", "TOOLS/run_checks.sh", body.target_dir],
            cwd=str(project_root),
            check=True,
            capture_output=True,
        )

    findings = await asyncio.to_thread(normalize_all, project_root / "DATA" / "outputs")
    run_id = db.create_analysis_run(repo_name=body.repo_name)
    for finding in findings:
        db.insert_finding(run_id, finding.to_dict())
    db.complete_analysis_run(run_id, len(findings))

    from collections import Counter

    cats = dict(Counter(f.category for f in findings))

    return {
        "success": True,
        "run_id": run_id,
        "total_findings": len(findings),
        "categories": cats,
        "message": f"Quick refresh complete — {len(findings)} findings stored.",
    }


@router.post("/secrets", summary="Run secrets detection on a directory")
async def scan_secrets(body: SecretsScanRequest, user: dict = Depends(get_current_user)):
    from CORE.engines.secrets_detector import SecretsDetector

    results = await asyncio.to_thread(SecretsDetector().scan_directory, body.target_dir)
    return {
        "success": True,
        "files_scanned": results["files_scanned"],
        "total_secrets": results["total_secrets"],
        "severity_breakdown": results["severity_breakdown"],
        "secret_types": results["secret_types_found"],
        "findings": results["findings"][:50],
    }


@router.post("/sca", summary="Run SCA (dependency vulnerability) scan")
async def scan_sca(body: SCAScanRequest, user: dict = Depends(get_current_user)):
    from CORE.engines.sca_scanner import SCAScanner

    scanner = SCAScanner(project_dir=body.project_dir)
    results = await asyncio.to_thread(scanner.scan)
    return {
        "success": True,
        "scanner": results["scanner"],
        "total_vulnerabilities": results["total_vulnerabilities"],
        "severity_breakdown": results["severity_breakdown"],
        "vulnerabilities": results["vulnerabilities"],
    }


@router.post("/ai-detection", summary="Run AI-generated code detection")
async def scan_ai_detection(body: AIDetectRequest, user: dict = Depends(get_current_user)):
    from CORE.engines.ai_code_detector import AICodeDetector

    detector = AICodeDetector(threshold=body.threshold)
    target = Path(body.target)

    if target.is_file():
        result = await asyncio.to_thread(detector.analyze_file, str(target))
        return {"success": True, "result": result}

    results = await asyncio.to_thread(detector.analyze_directory, str(target))
    return {
        "success": True,
        "total_files": results["total_files"],
        "flagged_files": results["flagged_files"],
        "flagged_percentage": results["flagged_percentage"],
        "files": results["files"][:50],
    }
