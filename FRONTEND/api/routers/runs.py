"""Runs router — query analysis results, trends, compliance, cost analytics."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from CORE.confidence_utils import calculate_confidence
from DATABASE.database import Database
from FRONTEND.api.deps import get_current_user, get_db
from FRONTEND.api.models import FindingsListOut, RunsListOut

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("", response_model=RunsListOut, summary="List recent analysis runs")
async def list_runs(
    limit: int = Query(10, ge=1, le=100),
    status: str | None = Query(None, description="Filter by status: completed | running | failed"),
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    runs = db.get_recent_runs(limit=limit * 3 if status else limit)
    if status:
        runs = [r for r in runs if r.get("status") == status]
        runs = runs[:limit]
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


@router.get("/{run_id}/findings", summary="Get findings for a run")
async def get_findings(
    run_id: int,
    severity: str | None = None,
    category: str | None = None,
    search: str = "",
    group_by: str | None = None,
    min_confidence: float | None = None,
    confirmed: bool | None = Query(
        None, description="If true, return only Confirmed Tier findings (96.4% precision gate)"
    ),
    exploit_tier: str | None = Query(
        None, description="Filter by exploit tier: verified-exploitable | verified-unexploitable | unverified"
    ),
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    findings = db.get_findings_with_explanations(run_id)

    # Apply Confirmed Tier classification to findings from DB
    from CORE.engines.confirmed_tier import ConfirmedTierEngine

    ct_engine = ConfirmedTierEngine()

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
        confidence = db_conf if db_conf is not None else calculate_confidence(f)
        if min_confidence is not None and confidence < min_confidence:
            continue

        # Classify confirmed tier on-the-fly (finding comes from DB, may not have it stored)
        ct_finding = dict(f)
        ct_finding["file"] = f.get("file_path", "")  # normalise field name
        ct_result = ct_engine.classify(ct_finding)
        in_confirmed = ct_result.in_confirmed_tier

        if confirmed is True and not in_confirmed:
            continue
        if confirmed is False and in_confirmed:
            continue

        f_exploit_tier = f.get("raw_output", {}).get("exploit_tier") if isinstance(f.get("raw_output"), dict) else None
        if exploit_tier and f_exploit_tier != exploit_tier:
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
                "confirmed_tier": in_confirmed,
                "confirmed_tier_signal": ct_result.reachability_signal,
                "exploit_tier": f_exploit_tier,
                "taint_source": f.get("taint_source"),
                "taint_path": f.get("taint_path"),
                "taint_confidence": f.get("taint_confidence"),
                "triage_verdict": f.get("triage_verdict"),
                "triage_reasoning": f.get("triage_reasoning"),
                "triage_confidence_delta": f.get("triage_confidence_delta"),
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


@router.get("/{run_id}/confirmed-summary", summary="Confirmed Tier summary for a run")
async def get_confirmed_summary(
    run_id: int,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """
    Returns the Confirmed Tier breakdown for a run:
    total findings → security-tier → confirmed count, precision context,
    and per-signal counts (exploit / taint / call_graph / none).

    This is the number to show in the PR merge-gate status check.
    """
    from CORE.engines.confirmed_tier import ConfirmedTierEngine

    findings = db.get_findings_with_explanations(run_id)
    engine = ConfirmedTierEngine()
    total = len(findings)
    confirmed = []
    signals: Counter = Counter()

    for f in findings:
        ct = dict(f)
        ct["file"] = f.get("file_path", "")
        result = engine.classify(ct)
        if result.in_confirmed_tier:
            confirmed.append(f)
            signals[result.reachability_signal] += 1

    n_confirmed = len(confirmed)
    return {
        "run_id": run_id,
        "total_findings": total,
        "confirmed_tier_count": n_confirmed,
        "confirmed_tier_pct": round(n_confirmed / total * 100, 1) if total else 0,
        "signals": dict(signals),
        "auto_block_safe": n_confirmed == 0,
        "precision_context": {
            "confirmed_tier_precision": "96.4%",
            "false_positive_tolerance": "<4%",
            "gate_criteria": "HIGH sev + 22-rule set + prod code + Bandit HIGH confidence",
        },
    }


@router.get(
    "/timeline",
    summary="Per-rule presence across the last N runs (Vulnerability Timeline)",
)
async def get_rule_timeline(
    limit: int = Query(30, ge=1, le=200),
    repo: str | None = None,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """
    Return data needed to render a Gantt-style Vulnerability Timeline:

        runs: ordered oldest → newest, each with id/started_at/repo_name
        rules: per-rule_id summary:
            - first_seen_run_id / last_seen_run_id
            - present_run_ids (list, ordered)
            - total_occurrences (sum of counts)
            - current_status: "open" if rule appears in newest run, else "resolved"
            - severity: latest observed severity
    """
    rows = db.get_rule_timeline(limit=limit, repo_name=repo)

    # Order runs oldest → newest
    runs_seen: dict[int, dict] = {}
    for r in rows:
        rid = r["run_id"]
        if rid not in runs_seen:
            runs_seen[rid] = {
                "id": rid,
                "started_at": str(r["started_at"]),
                "repo_name": r.get("repo_name"),
            }
    runs_sorted = sorted(runs_seen.values(), key=lambda x: x["started_at"])
    newest_run_id = runs_sorted[-1]["id"] if runs_sorted else None

    rules: dict[str, dict] = {}
    for r in rows:
        rule_id = r["rule_id"]
        entry = rules.setdefault(
            rule_id,
            {
                "rule_id": rule_id,
                "severity": (r.get("canonical_severity") or "low"),
                "first_seen_run_id": r["run_id"],
                "last_seen_run_id": r["run_id"],
                "present_run_ids": [],
                "total_occurrences": 0,
            },
        )
        entry["present_run_ids"].append(r["run_id"])
        entry["total_occurrences"] += int(r["count"])
        # severity is "high" → "medium" → "low" priority for display
        sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        if sev_order.get(r.get("canonical_severity") or "low", 9) < sev_order.get(entry["severity"], 9):
            entry["severity"] = r["canonical_severity"]
        entry["last_seen_run_id"] = r["run_id"]

    rules_list = []
    for entry in rules.values():
        entry["current_status"] = "open" if newest_run_id in entry["present_run_ids"] else "resolved"
        rules_list.append(entry)

    # Sort: open rules first, then HIGH severity first, then most-recently-seen
    sev_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    rules_list.sort(
        key=lambda r: (
            0 if r["current_status"] == "open" else 1,
            sev_rank.get(r["severity"], 9),
            -r["total_occurrences"],
            r["rule_id"],
        )
    )

    return {"runs": runs_sorted, "rules": rules_list}


@router.get(
    "/{run_id}/pr-risk",
    summary="Single 0..100 PR Risk Score (Review-Bottleneck Solver, v5.0.0 A5)",
)
async def get_pr_risk(
    run_id: int,
    refresh: bool = False,
    changed_lines: int = 0,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """
    Compose: HIGH count + reachability gate + exploit-verified count + taint
    touches + file-risk avg + size penalty. Returns score, band (green / amber /
    red), per-component contributions, and a plain-English explainer list.

    `changed_lines` is an optional hint from the caller (GitHub Action passes
    it from the PR diff). When zero we treat the PR as "size unknown".
    """
    cached = None if refresh else db.get_pr_risk_score(run_id)
    if cached:
        return {
            "run_id": run_id,
            "cached": True,
            "score": cached["score"],
            "band": cached["band"],
            "inputs": {
                "high_count": cached["high_count"],
                "reachable_high_count": cached["reachable_high_count"],
                "exploit_verified_count": cached["exploit_verified_count"],
                "taint_path_count": cached["taint_path_count"],
                "changed_lines": cached["changed_lines"],
            },
            "contributions": cached.get("contributions_json") or {},
            "explainer": cached.get("explainer_json") or [],
        }

    from CORE.engines.pr_risk import inputs_from_findings, predict_pr_risk

    findings = db.get_findings(run_id=run_id, limit=10000)
    # Use cached file risk scores if available; ignore findings outside the run.
    file_scores = [int(r.get("score", 0)) for r in db.get_file_risk_scores(run_id)]
    inputs = inputs_from_findings(findings, file_risk_scores=file_scores, changed_lines=changed_lines)
    result = predict_pr_risk(inputs)
    payload = result.to_dict()
    try:
        db.upsert_pr_risk_score(run_id, payload, changed_lines=changed_lines)
    except Exception:
        pass
    payload["run_id"] = run_id
    payload["cached"] = False
    return payload


@router.get(
    "/{run_id}/risk-map",
    summary="Compute (or fetch cached) per-file Heuristic Risk Predictor scores",
)
async def get_run_risk_map(
    run_id: int,
    refresh: bool = False,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """
    Returns the 0..100 risk score per file for this run.

    Default behaviour:
        1. Return cached scores from `file_risk_scores` if any exist.
        2. Otherwise compute on the fly using the run's findings + workspace git.
        3. Pass `refresh=true` to force a recompute.

    Workspace is the API server's CWD; computation gracefully degrades to
    zero-feature scores if the workspace is not a git repo or files are missing.
    """
    import os as _os

    cached = [] if refresh else db.get_file_risk_scores(run_id)
    if cached:
        return {
            "run_id": run_id,
            "cached": True,
            "total_files": len(cached),
            "files": cached,
        }

    findings = db.get_findings(run_id=run_id, limit=10000)
    from CORE.engines.risk_predictor import risk_map_payload, score_files

    scores = score_files(repo_dir=_os.getcwd(), findings=findings)
    persisted = 0
    for s in scores:
        try:
            db.upsert_file_risk_score(run_id, s.to_dict())
            persisted += 1
        except Exception:
            # DB failures are non-fatal; the response is still useful.
            continue

    payload = risk_map_payload(scores)
    payload["run_id"] = run_id
    payload["cached"] = False
    payload["persisted"] = persisted
    return payload


@router.get("/{run_id}/heatmap", summary="Aggregate finding density per file (Risk Heatmap)")
async def get_run_heatmap(
    run_id: int,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """
    Return one entry per file in the run with:
        - severity counts (high / medium / low)
        - top_rules: top 3 (rule_id, count) by frequency
        - risk_score: 0..100 normalized HIGH-density signal (clamped)

    Used by the dashboard's Risk Heatmap file tree (v5.0.0 Phase A.1).
    """
    findings = db.get_findings(run_id=run_id, limit=10000)
    by_file: dict[str, dict] = {}
    for f in findings:
        fp = f.get("file_path") or ""
        if not fp:
            continue
        entry = by_file.setdefault(
            fp,
            {
                "file_path": fp,
                "high": 0,
                "medium": 0,
                "low": 0,
                "total": 0,
                "rules": Counter(),
            },
        )
        sev = (f.get("canonical_severity") or "").lower()
        if sev in ("high", "critical"):
            entry["high"] += 1
        elif sev == "medium":
            entry["medium"] += 1
        else:
            entry["low"] += 1
        entry["total"] += 1
        rid = f.get("canonical_rule_id") or f.get("rule_id") or "UNKNOWN"
        entry["rules"][rid] += 1

    if not by_file:
        return {"run_id": run_id, "files": [], "max_high": 0, "max_total": 0}

    max_high = max(e["high"] for e in by_file.values()) or 1
    max_total = max(e["total"] for e in by_file.values()) or 1

    out = []
    for entry in sorted(by_file.values(), key=lambda x: (-x["high"], -x["total"], x["file_path"])):
        rules: Counter = entry["rules"]
        top_rules = [{"rule_id": r, "count": c} for r, c in rules.most_common(3)]
        # Risk score: 0..100. Weighted: 80% HIGH-density, 20% total-density.
        high_norm = entry["high"] / max_high
        total_norm = entry["total"] / max_total
        risk = int(round(min(100.0, 100.0 * (0.8 * high_norm + 0.2 * total_norm))))
        out.append(
            {
                "file_path": entry["file_path"],
                "high": entry["high"],
                "medium": entry["medium"],
                "low": entry["low"],
                "total": entry["total"],
                "risk_score": risk,
                "top_rules": top_rules,
            }
        )

    return {
        "run_id": run_id,
        "files": out,
        "max_high": max_high,
        "max_total": max_total,
    }


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


@router.get("/kpi/confirmed-fix-rate", summary="% Confirmed fixed KPI — the company metric")
async def confirmed_fix_rate_kpi(
    limit: int = Query(10, ge=1, le=50),
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """
    The single most important metric for the trust-layer business:
    what % of Confirmed Tier findings are marked as fixed (TP → fixed via feedback)?

    Target: >70% fix rate means the product creates real action, not noise.
    Formula: (findings where ground_truth='TP' AND feedback is_false_positive=False) /
             (all Confirmed Tier findings with feedback)

    Returns overall rate + per-repo breakdown across last N runs.
    """
    from CORE.engines.confirmed_tier import ConfirmedTierEngine

    engine = ConfirmedTierEngine()
    runs = db.get_recent_runs(limit=limit)

    per_repo: dict[str, dict] = {}
    total_confirmed_with_feedback = 0
    total_fixed = 0

    for run in runs:
        run_id = run["id"]
        repo = run.get("repo_name", "unknown")
        findings = db.get_findings_with_explanations(run_id)

        for f in findings:
            ct = dict(f)
            ct["file"] = f.get("file_path", "")
            if not engine.classify(ct).in_confirmed_tier:
                continue

            gt = f.get("ground_truth")
            if gt is None:
                continue  # no feedback yet

            entry = per_repo.setdefault(repo, {"confirmed": 0, "fixed": 0})
            entry["confirmed"] += 1
            total_confirmed_with_feedback += 1
            if gt == "TP":
                entry["fixed"] += 1
                total_fixed += 1

    overall_rate = (
        round(total_fixed / total_confirmed_with_feedback * 100, 1) if total_confirmed_with_feedback else None
    )
    target_met = overall_rate is not None and overall_rate >= 70.0

    return {
        "overall_fix_rate_pct": overall_rate,
        "target_pct": 70.0,
        "target_met": target_met,
        "total_confirmed_with_feedback": total_confirmed_with_feedback,
        "total_fixed": total_fixed,
        "status": "green" if target_met else ("yellow" if overall_rate and overall_rate >= 50 else "red"),
        "interpretation": (
            "Exceeds 70% target — trust layer is creating real action."
            if target_met
            else "Below 70% target — investigate FP rate or missing feedback."
        ),
        "per_repo": {
            repo: {
                "confirmed": v["confirmed"],
                "fixed": v["fixed"],
                "fix_rate_pct": round(v["fixed"] / v["confirmed"] * 100, 1) if v["confirmed"] else 0,
            }
            for repo, v in per_repo.items()
        },
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


@router.get("/{run_id}/attestation")
async def get_attestation(
    run_id: int,
    db: Database = Depends(get_db),
    _current_user: dict = Depends(get_current_user),
):
    """
    Return the SLSA-grade provenance attestation for a completed scan run.

    The bundle contains the attestation envelope (scan metadata) plus one or more
    signatures: always ECDSA-P256, optionally Dilithium3 (post-quantum) if available.
    """
    from CORE.engines.attestation import AttestationEngine, load_bundle_from_db

    row = db.get_attestation(run_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"No attestation found for run {run_id}")

    bundle = load_bundle_from_db(run_id, db)
    if bundle is None:
        raise HTTPException(status_code=500, detail="Attestation data is corrupt")

    verified = AttestationEngine().verify(bundle)
    algorithms = [s["algorithm"] for s in bundle.get("signatures", [])]

    return {
        "run_id": run_id,
        "key_id": row.get("key_id"),
        "created_at": str(row.get("created_at", "")),
        "signature_algorithms": algorithms,
        "post_quantum": "Dilithium3" in algorithms,
        "signature_valid": verified,
        "bundle": bundle,
    }


@router.get("/{run_id}/findings/{finding_id}/autofix", summary="Generate an LLM-powered patch for a finding")
async def get_autofix(
    run_id: int,
    finding_id: int,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Return a unified diff patch, confidence score, and explanation for a finding.

    The patch is generated by an LLM and validated by re-scanning the patched snippet.
    If the LLM is unavailable, falls back to the rule-based fix engine.
    """
    findings = db.get_findings_with_explanations(run_id)
    finding = next((f for f in findings if f["id"] == finding_id), None)
    if finding is None:
        raise HTTPException(status_code=404, detail=f"Finding {finding_id} not found in run {run_id}")

    from CORE.engines.autofix import AutofixEngine

    engine = AutofixEngine()
    result = engine.generate_patch(finding)

    if not result["patch"] and engine.can_fix(finding.get("canonical_rule_id", "")):
        rule_fix = engine.generate_fix(finding)
        if rule_fix:
            result["patch"] = (
                f"# Rule-based fix (line {rule_fix['line']}):\n- {rule_fix['original']}\n+ {rule_fix['fixed']}"
            )
            result["explanation"] = rule_fix["description"]
            result["confidence"] = engine.get_fix_confidence(finding.get("canonical_rule_id", ""))
            result["valid"] = True
            result["validation_note"] = "rule_based_fix"

    return {
        "finding_id": finding_id,
        "run_id": run_id,
        "rule_id": finding.get("canonical_rule_id"),
        "patch": result["patch"],
        "confidence": result["confidence"],
        "explanation": result["explanation"],
        "valid": result["valid"],
        "validation_note": result["validation_note"],
    }


@router.get("/{run_id}/sbom", summary="CycloneDX 1.4 SBOM for a run")
async def get_sbom(
    run_id: int,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Return the stored CycloneDX SBOM, or generate it on-the-fly from stored dependency findings."""
    sbom = db.get_run_sbom(run_id)
    if sbom is not None:
        return {"success": True, "run_id": run_id, "sbom": sbom}

    # On-the-fly generation from dependency_findings rows
    deps = db.get_dependency_findings(run_id)
    if not deps:
        raise HTTPException(status_code=404, detail="No supply-chain data found for this run")

    runs = db.get_recent_runs(limit=200)
    run = next((r for r in runs if r["id"] == run_id), None)
    repo_name = run["repo_name"] if run else "unknown"

    from CORE.engines.supply_chain import build_cyclonedx_sbom

    sbom = build_cyclonedx_sbom(run_id, repo_name, deps)
    return {"success": True, "run_id": run_id, "sbom": sbom}


@router.get("/{run_id}/review-bottleneck", summary="Review bottleneck analytics for a run")
async def get_review_bottleneck(
    run_id: int,
    days: int = Query(30, ge=1, le=365, description="Days of git history to analyze"),
    repo_path: str | None = Query(None, description="Filesystem path to the git repo; defaults to ACR-QA itself"),
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Return git-log-based review bottleneck metrics.

    Metrics: median review latency, reviewer load Gini, % merged without a
    review trailer, top-3 reviewer concentration, stale commit count.
    GitHub REST enrichment activates automatically when GITHUB_TOKEN is set.
    """
    run = db.get_analysis_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    from pathlib import Path as _Path

    from CORE.engines.review_bottleneck import analyze as _analyze

    target = repo_path or str(_Path(__file__).resolve().parent.parent.parent.parent)
    try:
        result = _analyze(repo_path=target, days=days)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc

    return {
        "success": True,
        "run_id": run_id,
        "repo_name": run.get("repo_name"),
        **result.to_dict(),
    }


@router.get("/{run_id}/diff", summary="Differential SAST — new findings only vs baseline run")
async def get_diff(
    run_id: int,
    baseline_run_id: int | None = Query(
        None,
        description="Run to compare against. Omit to auto-use the previous run for the same repo.",
    ),
    severity: str | None = None,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Return only findings in *run_id* whose fingerprint is NOT present in *baseline_run_id*.

    This is the core of Differential SAST: show developers only what changed since
    the last scan rather than the full noisy list.  Fingerprints are deterministic
    (repo-path + rule-id + line hash) so the same logical finding across runs has the
    same fingerprint even if line numbers shift slightly.
    """
    run = db.get_run_by_id(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    # Auto-resolve baseline: previous run for same repo
    if baseline_run_id is None:
        recent = db.get_recent_runs(limit=50)
        same_repo = [r for r in recent if r.get("repo_name") == run.get("repo_name") and r["id"] < run_id]
        if not same_repo:
            raise HTTPException(
                status_code=400,
                detail="No baseline run found for this repo. Pass baseline_run_id explicitly.",
            )
        baseline_run_id = max(r["id"] for r in same_repo)

    baseline_run = db.get_run_by_id(baseline_run_id)
    if not baseline_run:
        raise HTTPException(status_code=404, detail=f"Baseline run {baseline_run_id} not found")

    current_findings = db.get_findings_with_explanations(run_id)
    baseline_findings = db.get_findings_with_explanations(baseline_run_id)

    baseline_fingerprints: set[str] = {f["fingerprint"] for f in baseline_findings if f.get("fingerprint")}

    new_findings = [f for f in current_findings if f.get("fingerprint") not in baseline_fingerprints]
    fixed_count = sum(
        1 for f in baseline_findings if f.get("fingerprint") not in {x.get("fingerprint") for x in current_findings}
    )

    if severity:
        new_findings = [f for f in new_findings if f.get("severity", "").lower() == severity.lower()]

    return {
        "success": True,
        "run_id": run_id,
        "baseline_run_id": baseline_run_id,
        "summary": {
            "new_findings": len(new_findings),
            "fixed_since_baseline": fixed_count,
            "total_current": len(current_findings),
            "total_baseline": len(baseline_findings),
        },
        "new_findings": new_findings,
    }


@router.get("/{run_id}/supply-chain", summary="Supply-chain risk report for a run")
async def get_supply_chain(
    run_id: int,
    risk_level: str | None = None,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Return dependency findings with CVE data and risk scores."""
    deps = db.get_dependency_findings(run_id)
    if risk_level:
        deps = [d for d in deps if d.get("risk_level") == risk_level]

    summary = {
        "total": len(deps),
        "high_risk": sum(1 for d in deps if d.get("risk_level") == "high"),
        "medium_risk": sum(1 for d in deps if d.get("risk_level") == "medium"),
        "low_risk": sum(1 for d in deps if d.get("risk_level") == "low"),
        "total_cves": sum(d.get("cve_count", 0) for d in deps),
    }

    return {
        "success": True,
        "run_id": run_id,
        "summary": summary,
        "dependencies": deps,
    }
