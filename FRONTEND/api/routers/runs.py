"""Runs router — query analysis results, trends, compliance, cost analytics."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from DATABASE.database import Database
from FRONTEND.api.deps import get_current_user, get_db
from FRONTEND.api.models import FindingsListOut, RunsListOut

router = APIRouter(prefix="/runs", tags=["runs"])


def _confidence(finding: dict) -> float:
    score = 0.5
    explanation = finding.get("explanation_text", "") or ""
    rule_id = finding.get("canonical_rule_id", "") or ""
    severity = finding.get("canonical_severity", "low")
    category = finding.get("category", "")
    if rule_id and rule_id in explanation:
        score += 0.2
    if explanation:
        score += 0.1
    if severity == "high":
        score += 0.1
    if category == "security":
        score += 0.1
    return min(1.0, round(score, 2))


@router.get("", response_model=RunsListOut, summary="List recent analysis runs")
async def list_runs(
    limit: int = Query(10, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    runs = db.get_recent_runs(limit=limit)
    out = []
    for run in runs:
        summary = db.get_run_summary(run["id"])
        out.append(
            {
                "id": run["id"],
                "repo_name": run["repo_name"],
                "pr_number": run.get("pr_number"),
                "status": run["status"],
                "started_at": str(run["started_at"]),
                "total_findings": summary.get("findings_count", 0) if summary else 0,
                "high_count": summary.get("high_severity_count", 0) if summary else 0,
                "medium_count": summary.get("medium_severity_count", 0) if summary else 0,
                "low_count": summary.get("low_severity_count", 0) if summary else 0,
            }
        )
    return RunsListOut(runs=out)


@router.get("/{run_id}/findings", response_model=FindingsListOut, summary="Get findings for a run")
async def get_findings(
    run_id: int,
    severity: str | None = None,
    category: str | None = None,
    search: str = "",
    group_by: str | None = None,
    min_confidence: float | None = None,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    findings = db.get_findings_with_explanations(run_id)
    filtered = []

    for f in findings:
        if severity and f.get("canonical_severity") != severity:
            continue
        if category and f.get("category") != category:
            continue
        if search:
            searchable = f"{f.get('file_path', '')} {f.get('message', '')} {f.get('canonical_rule_id', '')}".lower()
            if search.lower() not in searchable:
                continue
        db_conf = f.get("confidence_score")
        confidence = db_conf if db_conf is not None else _confidence(f)
        if min_confidence is not None and confidence < min_confidence:
            continue
        filtered.append(
            {
                "id": f["id"],
                "rule_id": f.get("canonical_rule_id", f.get("rule_id")),
                "severity": f.get("canonical_severity", "low"),
                "category": f.get("category"),
                "file_path": f.get("file_path"),
                "line_number": f.get("line_number"),
                "message": f.get("message"),
                "explanation_text": f.get("explanation_text"),
                "model_name": f.get("model_name"),
                "latency_ms": f.get("latency_ms"),
                "tool": f.get("tool"),
                "confidence": confidence,
                "ground_truth": f.get("ground_truth"),
            }
        )

    if group_by == "rule":
        grouped: dict = {}
        for f in filtered:
            rid = f["rule_id"]
            if rid not in grouped:
                grouped[rid] = {
                    "rule_id": rid,
                    "count": 0,
                    "severity": f["severity"],
                    "category": f["category"],
                    "findings": [],
                }
            grouped[rid]["count"] += 1
            grouped[rid]["findings"].append(f)
        return {"success": True, "grouped": True, "groups": list(grouped.values()), "total": len(filtered)}

    return FindingsListOut(findings=filtered, total=len(filtered))


@router.get("/{run_id}/stats", summary="Get severity/cost stats for a run")
async def get_stats(
    run_id: int,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    summary = db.get_run_summary(run_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Run not found")
    return {
        "success": True,
        "run_id": run_id,
        "repo_name": summary.get("repo_name"),
        "status": summary.get("status"),
        "total_findings": summary.get("findings_count", 0),
        "high": summary.get("high_severity_count", 0),
        "medium": summary.get("medium_severity_count", 0),
        "low": summary.get("low_severity_count", 0),
        "explanations_count": summary.get("explanations_count", 0),
        "avg_latency_ms": float(summary.get("avg_explanation_latency", 0) or 0),
        "total_cost_usd": float(summary.get("total_cost", 0) or 0),
    }


@router.get("/{run_id}/summary", summary="Generate PR-style markdown summary")
async def get_pr_summary(
    run_id: int,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    runs = db.get_recent_runs(limit=100)
    run = next((r for r in runs if r["id"] == run_id), None)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    findings = db.get_findings(run_id)
    sev_counts = Counter(f.get("severity", "low") for f in findings)
    cat_counts = Counter(f.get("category", "unknown") for f in findings)
    critical = [f for f in findings if f.get("severity") in ("high", "critical")]

    md = f"""## ACR-QA Analysis Summary

**Total Issues:** {len(findings)}
**Critical/High:** {sev_counts.get('high', 0) + sev_counts.get('critical', 0)}
**Medium:** {sev_counts.get('medium', 0)}
**Low:** {sev_counts.get('low', 0)}

### Top Categories
"""
    for cat, count in cat_counts.most_common(3):
        md += f"- **{cat}**: {count}\n"

    if critical:
        md += f"\n### Critical Issues ({len(critical)})\n"
        for f in critical[:3]:
            md += f"- {f.get('canonical_rule_id', 'UNKNOWN')}: {f.get('message', '')[:60]}\n"

    return {
        "success": True,
        "run_id": run_id,
        "summary_markdown": md,
        "stats": {
            "total": len(findings),
            "high": sev_counts.get("high", 0) + sev_counts.get("critical", 0),
            "medium": sev_counts.get("medium", 0),
            "low": sev_counts.get("low", 0),
        },
    }


@router.get("/{run_id}/compliance", summary="OWASP Top 10 compliance report")
async def get_compliance(
    run_id: int,
    user: dict = Depends(get_current_user),
):
    from scripts.generate_compliance_report import get_compliance_data

    data = get_compliance_data(run_id=run_id)
    if isinstance(data, str):
        raise HTTPException(status_code=404, detail=data)
    return {"success": True, **data}


@router.get("/{run_id}/cost-benefit", summary="Cost-benefit analysis for a run")
async def cost_benefit(
    run_id: int,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    findings = db.get_findings(run_id)
    if not findings:
        raise HTTPException(status_code=404, detail="No findings found")

    total_cost = sum(float(f.get("cost_usd", 0) or 0) for f in findings)
    hours_saved = sum(
        0.5
        if (f.get("severity") or "low").lower() == "high"
        else 0.25
        if (f.get("severity") or "low").lower() == "medium"
        else 0.083
        for f in findings
    )
    dev_cost_saved = hours_saved * 75
    roi = dev_cost_saved / total_cost if total_cost > 0 else float("inf")

    return {
        "success": True,
        "analysis_cost_usd": round(total_cost, 4),
        "hours_saved": round(hours_saved, 1),
        "dev_cost_saved_usd": round(dev_cost_saved, 2),
        "roi_multiplier": round(roi, 1) if roi != float("inf") else "∞",
        "cost_per_finding": round(total_cost / len(findings), 4) if findings else 0,
        "total_findings": len(findings),
    }
