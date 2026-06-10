"""Workbench endpoints — Phase 5.

Tabs backed here:
  Query           GET /v1/workbench/query
  NL→Params       POST /v1/workbench/nl-query
  Rule Perf       GET /v1/workbench/rule-performance
  Audit Log       GET /v1/workbench/audit-log
  Labelling       GET /v1/workbench/labels
                  PATCH /v1/workbench/labels/{id}
                  GET /v1/workbench/labels/export
  Attack Path     GET /v1/workbench/attack-paths/{vuln_id}
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from fastapi import APIRouter, Depends, HTTPException, Query  # noqa: E402
from fastapi.responses import StreamingResponse  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from DATABASE.database import Database  # noqa: E402
from FRONTEND.api.deps import get_current_user, get_db  # noqa: E402

router = APIRouter(prefix="/v1/workbench", tags=["workbench"])

# ── Pydantic models ────────────────────────────────────────────────────────────


class QueryParams(BaseModel):
    severity: str | None = None
    rule: str | None = None
    status: str | None = None
    file: str | None = None
    owner: str | None = None
    limit: int = 50
    offset: int = 0


class NLQueryRequest(BaseModel):
    q: str
    use_llm: bool = False


class LabelPatch(BaseModel):
    ground_truth: str  # TP | FP | TN | FN
    reasoning: str = ""


# ── NL → params parser ─────────────────────────────────────────────────────────

_SEV = re.compile(r"\b(high|medium|med|low)\b", re.I)
_STATUS = re.compile(r"\b(open|fixed|verified|dismissed|regressed|assigned|detected|confirmed|in[_\s]progress)\b", re.I)
_RULE = re.compile(r"\b([A-Z][A-Z0-9]{2,}-\d+)\b")
_FILE = re.compile(r"\b([\w./]+\.(?:py|js|ts|go|rb|java|c|cpp|h|yml|yaml|json))\b", re.I)
_OWNER = re.compile(r"@([\w.-]+)")
_LIMIT = re.compile(r"\b(?:top|first|last)\s+(\d+)\b", re.I)


def _parse_nl(q: str) -> QueryParams:
    params = QueryParams()
    if m := _SEV.search(q):
        raw = m.group(1).lower()
        params.severity = "medium" if raw == "med" else raw
    if m := _STATUS.search(q):
        raw = m.group(1).lower().replace(" ", "_").replace("-", "_")
        params.status = raw
    if m := _RULE.search(q):
        params.rule = m.group(1)
    if m := _FILE.search(q):
        params.file = m.group(1)
    if m := _OWNER.search(q):
        params.owner = m.group(1)
    if m := _LIMIT.search(q):
        params.limit = min(int(m.group(1)), 200)
    return params


async def _llm_parse_nl(q: str) -> QueryParams:
    """Use Groq to extract structured params from freeform query."""
    api_key = os.getenv("GROQ_API_KEY_1") or os.getenv("GROQ_API_KEY")
    if not api_key:
        return _parse_nl(q)

    try:
        from groq import Groq

        client = Groq(api_key=api_key)
        system = (
            "You are a query parser for a security findings database. "
            "Extract structured filter params from the user query. "
            'Return ONLY valid JSON: {"severity":"high|medium|low|null","rule":"RULE-ID|null",'
            '"status":"open|fixed|dismissed|regressed|null","file":"path|null","owner":"name|null","limit":50}'
        )
        resp = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "system", "content": system}, {"role": "user", "content": q}],
            max_tokens=200,
            temperature=0,
        )
        text = resp.choices[0].message.content or "{}"
        # Extract JSON block if wrapped
        if m := re.search(r"\{.*\}", text, re.S):
            data = json.loads(m.group())
            return QueryParams(**{k: v for k, v in data.items() if v not in (None, "null", "")})
    except Exception:
        pass
    return _parse_nl(q)


# ── Routes ─────────────────────────────────────────────────────────────────────


@router.get("/query", summary="Parameterized vulnerability + finding query")
async def query_findings(
    severity: str | None = None,
    rule: str | None = None,
    status: str | None = None,
    file: str | None = None,
    owner: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    conditions, params = [], []
    if severity:
        conditions.append("v.severity = %s")
        params.append(severity)
    if rule:
        conditions.append("v.canonical_rule_id ILIKE %s")
        params.append(f"%{rule}%")
    if status:
        conditions.append("v.status = %s")
        params.append(status)
    if file:
        conditions.append("v.file_path ILIKE %s")
        params.append(f"%{file}%")
    if owner:
        conditions.append("v.owner ILIKE %s")
        params.append(f"%{owner}%")

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    params.extend([limit, offset])

    rows = db.execute(
        f"""
        SELECT v.id, v.short_id, v.canonical_rule_id, v.severity, v.status,
               v.file_path, v.message AS title, v.owner, v.first_seen_at, v.updated_at,
               COUNT(f.id) AS finding_count
        FROM vulnerabilities v
        LEFT JOIN findings f ON f.vulnerability_id = v.id
        {where}
        GROUP BY v.id
        ORDER BY CASE v.severity WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                 v.updated_at DESC NULLS LAST
        LIMIT %s OFFSET %s
        """,
        tuple(params),
        fetch=True,
    )

    total_rows = db.execute(
        f"SELECT COUNT(DISTINCT v.id) AS n FROM vulnerabilities v {where}",
        tuple(params[:-2]),
        fetch=True,
    )
    total = int(total_rows[0]["n"]) if total_rows else 0

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "results": [dict(r) for r in rows] if rows else [],
    }


@router.post("/nl-query", summary="Natural-language → parameterized query")
async def nl_query(
    body: NLQueryRequest,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    params = await _llm_parse_nl(body.q) if body.use_llm else _parse_nl(body.q)
    # Run the actual query with the parsed params
    result = await query_findings(
        severity=params.severity,
        rule=params.rule,
        status=params.status,
        file=params.file,
        owner=params.owner,
        limit=params.limit,
        offset=params.offset,
        user=user,
        db=db,
    )
    return {"parsed": params.model_dump(), **result}


@router.get("/rule-performance", summary="Per-rule fire rate + TP/FP accuracy")
async def rule_performance(
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    rows = db.execute(
        """
        SELECT
            f.canonical_rule_id                                         AS rule_id,
            COUNT(f.id)                                                 AS fire_count,
            COUNT(f.id) FILTER (WHERE f.triage_verdict = 'TP')         AS tp_count,
            COUNT(f.id) FILTER (WHERE f.triage_verdict = 'FP')         AS fp_count,
            COUNT(f.id) FILTER (WHERE f.ground_truth IS NOT NULL)      AS labelled_count,
            COUNT(f.id) FILTER (WHERE f.ground_truth = 'TP')           AS gt_tp,
            COUNT(f.id) FILTER (WHERE f.ground_truth = 'FP')           AS gt_fp,
            ROUND(AVG(f.confidence_score)::numeric, 3)                 AS avg_confidence,
            COUNT(DISTINCT f.run_id)                                    AS runs_seen,
            MAX(ar.started_at)                                          AS last_seen
        FROM findings f
        JOIN analysis_runs ar ON ar.id = f.run_id
        WHERE f.canonical_rule_id IS NOT NULL
        GROUP BY f.canonical_rule_id
        ORDER BY fire_count DESC
        LIMIT %s
        """,
        (limit,),
        fetch=True,
    )

    result = []
    for r in rows or []:
        fire = int(r["fire_count"] or 0)
        tp = int(r["tp_count"] or 0)
        fp = int(r["fp_count"] or 0)
        labelled = int(r["labelled_count"] or 0)
        gt_tp = int(r["gt_tp"] or 0)
        gt_fp = int(r["gt_fp"] or 0)
        triaged = tp + fp
        tp_rate = round(tp / triaged, 3) if triaged > 0 else None
        noise_ratio = round(fp / fire, 3) if fire > 0 else 0.0
        gt_accuracy = round(gt_tp / (gt_tp + gt_fp), 3) if (gt_tp + gt_fp) > 0 else None
        result.append(
            {
                "rule_id": r["rule_id"],
                "fire_count": fire,
                "tp_count": tp,
                "fp_count": fp,
                "tp_rate": tp_rate,
                "noise_ratio": noise_ratio,
                "labelled_count": labelled,
                "gt_tp": gt_tp,
                "gt_fp": gt_fp,
                "gt_accuracy": gt_accuracy,
                "avg_confidence": float(r["avg_confidence"] or 0),
                "runs_seen": int(r["runs_seen"] or 0),
                "last_seen": str(r["last_seen"]) if r["last_seen"] else None,
            }
        )

    return {"total": len(result), "rules": result}


@router.get("/audit-log", summary="Org-wide vulnerability lifecycle event feed")
async def audit_log(
    limit: int = Query(100, ge=1, le=500),
    repo: str | None = None,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    conditions = []
    params: list = []
    if repo:
        conditions.append("ar.repo_name = %s")
        params.append(repo)
    where = ("AND " + " AND ".join(conditions)) if conditions else ""
    params.append(limit)

    rows = db.execute(
        f"""
        SELECT
            v.id            AS vuln_id,
            v.short_id,
            v.canonical_rule_id,
            v.severity,
            v.status,
            v.owner,
            v.file_path,
            ar.repo_name,
            f.triage_verdict,
            f.confidence_score,
            ar.started_at   AS event_at,
            'scan'          AS event_type
        FROM findings f
        JOIN analysis_runs ar ON ar.id = f.run_id
        LEFT JOIN vulnerabilities v ON v.id = f.vulnerability_id
        WHERE v.id IS NOT NULL {where}
        ORDER BY ar.started_at DESC
        LIMIT %s
        """,
        tuple(params),
        fetch=True,
    )

    return {
        "total": len(rows),
        "events": [dict(r) for r in rows] if rows else [],
    }


@router.get("/labels", summary="Findings queue for ground-truth labelling")
async def get_labels(
    run_id: int | None = None,
    unlabelled_only: bool = True,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    conditions, params = [], []
    if run_id:
        conditions.append("f.run_id = %s")
        params.append(run_id)
    if unlabelled_only:
        conditions.append("f.ground_truth IS NULL")
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    params.extend([limit, offset])

    rows = db.execute(
        f"""
        SELECT f.id, f.canonical_rule_id, f.canonical_severity, f.file_path,
               f.line_number, f.message, f.ground_truth, f.triage_verdict,
               f.confidence_score, ar.repo_name, ar.started_at
        FROM findings f
        JOIN analysis_runs ar ON ar.id = f.run_id
        {where}
        ORDER BY f.confidence_score DESC NULLS LAST, ar.started_at DESC
        LIMIT %s OFFSET %s
        """,
        tuple(params),
        fetch=True,
    )

    total_rows = db.execute(
        f"SELECT COUNT(*) AS n FROM findings f JOIN analysis_runs ar ON ar.id = f.run_id {where}",
        tuple(params[:-2]),
        fetch=True,
    )
    total = int(total_rows[0]["n"]) if total_rows else 0

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "findings": [dict(r) for r in rows] if rows else [],
    }


@router.patch("/labels/{finding_id}", summary="Set ground-truth label for a finding")
async def set_label(
    finding_id: int,
    body: LabelPatch,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    try:
        db.update_finding_ground_truth(finding_id, body.ground_truth)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    # Optionally persist reasoning as triage_reasoning if provided
    if body.reasoning:
        try:
            db.execute(
                "UPDATE findings SET triage_reasoning = %s WHERE id = %s",
                (body.reasoning[:1000], finding_id),
            )
        except Exception:
            pass
    return {"finding_id": finding_id, "ground_truth": body.ground_truth, "updated": True}


@router.get("/labels/export", summary="Export labelled findings as JSONL for model training")
async def export_labels(
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    rows = db.execute(
        """
        SELECT f.id, f.canonical_rule_id, f.canonical_severity, f.file_path,
               f.line_number, f.message, f.ground_truth, f.triage_verdict,
               f.triage_reasoning, f.confidence_score, f.evidence,
               ar.repo_name
        FROM findings f
        JOIN analysis_runs ar ON ar.id = f.run_id
        WHERE f.ground_truth IS NOT NULL
        ORDER BY f.id
        """,
        fetch=True,
    )

    def generate():
        for r in rows or []:
            record = {
                "id": r["id"],
                "rule": r["canonical_rule_id"],
                "severity": r["canonical_severity"],
                "file": r["file_path"],
                "line": r["line_number"],
                "message": r["message"],
                "ground_truth": r["ground_truth"],
                "triage": r["triage_verdict"],
                "reasoning": r["triage_reasoning"],
                "confidence": float(r["confidence_score"]) if r["confidence_score"] else None,
                "repo": r["repo_name"],
            }
            yield json.dumps(record) + "\n"

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={"Content-Disposition": "attachment; filename=acrqa-labels.jsonl"},
    )


@router.get("/attack-paths/{vuln_id}", summary="Taint-chain attack path from a vulnerability")
async def attack_paths(
    vuln_id: int,
    depth: int = Query(3, ge=1, le=6),
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """BFS up to `depth` hops through taint-chain edges."""
    visited: set[int] = set()
    frontier = [vuln_id]
    nodes: list[dict] = []
    edges: list[dict] = []

    for hop in range(depth):
        if not frontier:
            break
        placeholders = ",".join(["%s"] * len(frontier))
        rows = db.execute(
            f"""
            SELECT v.id, v.short_id, v.canonical_rule_id, v.severity, v.status,
                   v.file_path, tc.vuln_id AS src_id, tc.score
            FROM mv_vuln_taint_chain tc
            JOIN vulnerabilities v ON v.id = tc.related_id
            WHERE tc.vuln_id IN ({placeholders})
              AND tc.related_id NOT IN ({placeholders if visited else 'SELECT NULL'})
            LIMIT 30
            """,
            tuple(frontier) + (tuple(visited) if visited else ()),
            fetch=True,
        )

        next_frontier = []
        for r in rows or []:
            if r["id"] not in visited:
                nodes.append(
                    {
                        "id": r["id"],
                        "short_id": r["short_id"],
                        "rule": r["canonical_rule_id"],
                        "severity": r["severity"],
                        "status": r["status"],
                        "file": r["file_path"],
                        "hop": hop + 1,
                    }
                )
                edges.append({"from": r["src_id"], "to": r["id"], "score": float(r["score"])})
                next_frontier.append(r["id"])
                visited.add(r["id"])

        frontier = next_frontier

    # Also add the root node
    root = db.get_vulnerability(vuln_id)
    if root:
        nodes.insert(
            0,
            {
                "id": root["id"],
                "short_id": root["short_id"],
                "rule": root["canonical_rule_id"],
                "severity": root["severity"],
                "status": root["status"],
                "file": root["file_path"],
                "hop": 0,
            },
        )

    return {
        "root_vuln_id": vuln_id,
        "depth": depth,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
    }
