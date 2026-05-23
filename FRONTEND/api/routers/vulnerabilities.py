"""Vulnerabilities router — Phase 0 persistent Vulnerability objects.

Endpoints:
    GET  /v1/vulnerabilities                — list with filters + pagination
    GET  /v1/vulnerabilities/:id            — single vuln by PK
    GET  /v1/vulnerabilities/by/:short_id   — single vuln by short URL-safe ID
    PATCH /v1/vulnerabilities/:id/status    — lifecycle transition
    PATCH /v1/vulnerabilities/:id/owner     — assign / unassign owner
    GET  /v1/vulnerabilities/:id/findings   — all findings linked to this vuln
"""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from DATABASE.database import Database
from FRONTEND.api.deps import get_current_user, get_db

router = APIRouter(prefix="/vulnerabilities", tags=["vulnerabilities"])


# ── Pydantic models ───────────────────────────────────────────────────────────


class VulnerabilityOut(BaseModel):
    id: int
    fingerprint: str
    short_id: str
    canonical_rule_id: str
    file_path: str
    status: str
    owner: str | None = None
    severity: str
    category: str | None = None
    message: str | None = None
    first_seen_run_id: int | None = None
    first_seen_at: str | None = None
    last_seen_at: str | None = None
    resolved_at: str | None = None
    created_at: str
    updated_at: str


class VulnerabilityListOut(BaseModel):
    total: int
    limit: int
    offset: int
    vulnerabilities: list[VulnerabilityOut]


class StatusPatchRequest(BaseModel):
    status: str


class OwnerPatchRequest(BaseModel):
    owner: str | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────


def _serialize(row: dict) -> dict:
    return {
        "id": row["id"],
        "fingerprint": row["fingerprint"],
        "short_id": row["short_id"],
        "canonical_rule_id": row["canonical_rule_id"],
        "file_path": row["file_path"],
        "status": row["status"],
        "owner": row.get("owner"),
        "severity": row["severity"],
        "category": row.get("category"),
        "message": row.get("message"),
        "first_seen_run_id": row.get("first_seen_run_id"),
        "first_seen_at": str(row["first_seen_at"]) if row.get("first_seen_at") else None,
        "last_seen_at": str(row["last_seen_at"]) if row.get("last_seen_at") else None,
        "resolved_at": str(row["resolved_at"]) if row.get("resolved_at") else None,
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }


# ── Routes ────────────────────────────────────────────────────────────────────


@router.get("", response_model=VulnerabilityListOut, summary="List vulnerabilities")
async def list_vulnerabilities(
    status: str | None = Query(default=None, description="Filter by lifecycle status"),
    severity: str | None = Query(default=None, description="Filter by severity (high/medium/low)"),
    rule: str | None = Query(default=None, description="Filter by canonical_rule_id"),
    owner: str | None = Query(default=None, description="Filter by owner"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    total = db.count_vulnerabilities(status=status, severity=severity)
    rows = db.list_vulnerabilities(
        status=status,
        severity=severity,
        canonical_rule_id=rule,
        owner=owner,
        limit=limit,
        offset=offset,
    )
    return VulnerabilityListOut(
        total=total,
        limit=limit,
        offset=offset,
        vulnerabilities=[VulnerabilityOut(**_serialize(r)) for r in rows],
    )


@router.get("/by/{short_id}", response_model=VulnerabilityOut, summary="Get vulnerability by short ID")
async def get_vulnerability_by_short(
    short_id: str,
    _user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    row = db.get_vulnerability_by_short_id(short_id)
    if row is None:
        raise HTTPException(status_code=404, detail="vulnerability not found")
    return VulnerabilityOut(**_serialize(row))


@router.get("/{vuln_id}", response_model=VulnerabilityOut, summary="Get vulnerability by ID")
async def get_vulnerability(
    vuln_id: int,
    _user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    row = db.get_vulnerability(vuln_id)
    if row is None:
        raise HTTPException(status_code=404, detail="vulnerability not found")
    return VulnerabilityOut(**_serialize(row))


@router.patch("/{vuln_id}/status", response_model=VulnerabilityOut, summary="Transition lifecycle status")
async def patch_status(
    vuln_id: int,
    body: StatusPatchRequest,
    _user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    if db.get_vulnerability(vuln_id) is None:
        raise HTTPException(status_code=404, detail="vulnerability not found")
    if body.status not in db.VULN_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"invalid status '{body.status}'; must be one of {sorted(db.VULN_STATUSES)}",
        )
    db.update_vulnerability_status(vuln_id, body.status)
    return VulnerabilityOut(**_serialize(db.get_vulnerability(vuln_id)))


@router.patch("/{vuln_id}/owner", response_model=VulnerabilityOut, summary="Assign or unassign owner")
async def patch_owner(
    vuln_id: int,
    body: OwnerPatchRequest,
    _user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    if db.get_vulnerability(vuln_id) is None:
        raise HTTPException(status_code=404, detail="vulnerability not found")
    db.update_vulnerability_owner(vuln_id, body.owner)
    return VulnerabilityOut(**_serialize(db.get_vulnerability(vuln_id)))


@router.get("/{vuln_id}/findings", summary="List all findings linked to this vulnerability")
async def get_vuln_findings(
    vuln_id: int,
    _user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    if db.get_vulnerability(vuln_id) is None:
        raise HTTPException(status_code=404, detail="vulnerability not found")
    findings = db.get_vulnerability_findings(vuln_id)
    return {"vulnerability_id": vuln_id, "findings": [dict(f) for f in findings]}
