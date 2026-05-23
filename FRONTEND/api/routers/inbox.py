"""Inbox router — Phase 2 pre-categorised vulnerability feed.

Endpoints:
    GET  /v1/inbox            — categorised inbox sections for the current user
    POST /v1/inbox/bulk       — bulk status/owner patch across multiple vuln IDs
"""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from DATABASE.database import Database
from FRONTEND.api.deps import get_current_user, get_db

router = APIRouter(prefix="/inbox", tags=["inbox"])


# ── Pydantic models ───────────────────────────────────────────────────────────


class InboxResponse(BaseModel):
    regressions: list[dict]
    stale_tps: list[dict]
    disagreements: list[dict]
    new_vulns: list[dict]
    assigned_to_me: list[dict]
    pr_vulns: list[dict]
    total: int


class BulkPatchRequest(BaseModel):
    vuln_ids: list[int]
    status: str | None = None
    owner: str | None = None
    clear_owner: bool = False


class BulkPatchResponse(BaseModel):
    updated: int
    vuln_ids: list[int]


# ── Routes ────────────────────────────────────────────────────────────────────


@router.get("", response_model=InboxResponse, summary="Get inbox feed")
async def get_inbox(
    stale_days: int = Query(default=7, ge=1, le=90, description="Days without update before a confirmed TP is 'stale'"),
    limit: int = Query(default=50, ge=1, le=200),
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Return inbox sections pre-categorised by priority:
    regressions → stale_tps → disagreements → new_vulns → assigned_to_me → pr_vulns.
    """
    owner = user.get("username") or user.get("email")
    data = db.get_inbox(owner=owner, stale_days=stale_days, limit=limit)

    # Serialize datetime objects
    def _serialize_list(rows: list[dict]) -> list[dict]:
        result = []
        for row in rows:
            r = {}
            for k, v in row.items():
                r[k] = str(v) if hasattr(v, "isoformat") else v
            result.append(r)
        return result

    regressions = _serialize_list(data.get("regressions", []))
    stale_tps = _serialize_list(data.get("stale_tps", []))
    disagreements = _serialize_list(data.get("disagreements", []))
    new_vulns = _serialize_list(data.get("new_vulns", []))
    assigned_to_me = _serialize_list(data.get("assigned_to_me", []))
    pr_vulns = _serialize_list(data.get("pr_vulns", []))

    total = len(regressions) + len(stale_tps) + len(disagreements) + len(new_vulns) + len(assigned_to_me)

    return InboxResponse(
        regressions=regressions,
        stale_tps=stale_tps,
        disagreements=disagreements,
        new_vulns=new_vulns,
        assigned_to_me=assigned_to_me,
        pr_vulns=pr_vulns,
        total=total,
    )


@router.post("/bulk", response_model=BulkPatchResponse, summary="Bulk-patch status or owner")
async def bulk_patch(
    body: BulkPatchRequest,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Apply status or owner change to multiple vulnerabilities at once.

    - Set `status` to transition all matching vulns.
    - Set `owner` to assign; set `clear_owner=true` to unassign.
    """
    if not body.vuln_ids:
        return BulkPatchResponse(updated=0, vuln_ids=[])

    updated = 0
    for vid in body.vuln_ids:
        try:
            if body.status:
                db.update_vulnerability_status(vid, body.status)
                updated += 1
            if body.owner or body.clear_owner:
                db.update_vulnerability_owner(vid, None if body.clear_owner else body.owner)
                if not body.status:
                    updated += 1
        except Exception:
            pass

    return BulkPatchResponse(updated=updated, vuln_ids=body.vuln_ids)
