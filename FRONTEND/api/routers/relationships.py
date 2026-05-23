"""Relationship endpoints — cross-vuln graph edges, rule stats, author views, global search."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from fastapi import APIRouter, Depends, HTTPException, Query  # noqa: E402

from DATABASE.database import Database  # noqa: E402
from FRONTEND.api.deps import get_current_user, get_db  # noqa: E402

router = APIRouter(prefix="/v1", tags=["relationships"])


@router.get(
    "/vulnerabilities/{vuln_id}/related",
    summary="Related vulnerabilities via rule/file/taint edges",
)
async def get_related(
    vuln_id: int,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    vuln = db.get_vulnerability(vuln_id)
    if not vuln:
        raise HTTPException(status_code=404, detail=f"Vulnerability {vuln_id} not found")
    related = db.get_related_vulnerabilities(vuln_id)
    return {"vuln_id": vuln_id, "total": len(related), "related": related}


@router.get(
    "/rules/{rule_id}/stats",
    summary="Aggregate stats for a canonical rule ID",
)
async def get_rule_stats(
    rule_id: str,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    stats = db.get_rule_stats(rule_id)
    return stats


@router.get(
    "/authors/{author}/vulnerabilities",
    summary="Open vulnerabilities assigned to an author",
)
async def get_author_vulns(
    author: str,
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    vulns = db.get_author_vulnerabilities(author, limit=limit)
    return {"author": author, "total": len(vulns), "vulnerabilities": vulns}


@router.get(
    "/search",
    summary="Cross-object search: vulns, rules, authors",
)
async def global_search(
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(10, ge=1, le=50),
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    if len(q.strip()) < 1:
        return {"q": q, "vulns": [], "rules": [], "authors": []}
    results = db.search_objects(q.strip(), limit=limit)
    return {"q": q, **results}
