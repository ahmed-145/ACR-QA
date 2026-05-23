"""Fleet posture aggregation endpoints — Phase 4."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from fastapi import APIRouter, Depends, Query  # noqa: E402

from DATABASE.database import Database  # noqa: E402
from FRONTEND.api.deps import get_current_user, get_db  # noqa: E402

router = APIRouter(prefix="/v1/fleet", tags=["fleet"])

# OWASP Top 10 → canonical rule ID prefix mapping
OWASP_MAP = {
    "A01:Access Control": ["SECURITY-001", "SECURITY-003"],
    "A02:Cryptographic": ["SECURITY-006", "HARDCODE"],
    "A03:Injection": ["SECURITY-002", "SECURITY-004", "SECURITY-005"],
    "A04:Insecure Design": ["PATTERN", "COMPLEXITY"],
    "A05:Misconfiguration": ["IaC", "SECURITY-007"],
    "A06:Components": ["SUPPLY"],
    "A07:Authentication": ["HARDCODE-001", "SECURITY-003"],
    "A08:Integrity": ["SUPPLY", "IaC"],
    "A09:Logging": ["SECURITY-008"],
    "A10:SSRF": ["SECURITY-009"],
}

# STRIDE mapping: finding category prefix → STRIDE threat
STRIDE_MAP = {
    "Spoofing": ["HARDCODE", "SECURITY-003", "SECURITY-006"],
    "Tampering": ["SECURITY-001", "SECURITY-002", "SECURITY-004", "SECURITY-005"],
    "Repudiation": ["SECURITY-008"],
    "Information Disclosure": ["SECURITY-006", "HARDCODE-001", "SECURITY-002"],
    "Denial of Service": ["COMPLEXITY", "PATTERN-001"],
    "Elevation of Privilege": ["SECURITY-001", "SECURITY-003", "SECURITY-007"],
}


@router.get("", summary="Fleet-wide posture summary per repo")
async def fleet_summary(
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Aggregated per-repo posture: open vulns, severity breakdown, trend, top rule."""
    # Per-repo vuln aggregation from vulnerabilities table
    repo_rows = db.execute(
        """
        SELECT
            ar.repo_name,
            COUNT(v.id)                                            AS total_vulns,
            COUNT(v.id) FILTER (WHERE v.status NOT IN ('dismissed','fixed','verified')) AS open_vulns,
            COUNT(v.id) FILTER (WHERE v.severity = 'high'
                                  AND v.status NOT IN ('dismissed','fixed','verified')) AS open_high,
            COUNT(v.id) FILTER (WHERE v.severity = 'medium'
                                  AND v.status NOT IN ('dismissed','fixed','verified')) AS open_med,
            COUNT(v.id) FILTER (WHERE v.severity = 'low'
                                  AND v.status NOT IN ('dismissed','fixed','verified')) AS open_low,
            COUNT(v.id) FILTER (WHERE v.status = 'regressed')     AS regressions,
            MAX(ar.started_at)                                     AS last_scan,
            COUNT(DISTINCT ar.id)                                  AS total_scans
        FROM analysis_runs ar
        LEFT JOIN findings f ON f.run_id = ar.id
        LEFT JOIN vulnerabilities v ON v.id = f.vulnerability_id
        GROUP BY ar.repo_name
        ORDER BY open_high DESC, open_vulns DESC
        LIMIT %s
        """,
        (limit,),
        fetch=True,
    )

    # Org totals
    org_rows = db.execute(
        """
        SELECT
            COUNT(*) FILTER (WHERE status NOT IN ('dismissed','fixed','verified')) AS open_total,
            COUNT(*) FILTER (WHERE status = 'regressed')                           AS regressions,
            COUNT(*) FILTER (WHERE severity = 'high'
                              AND status NOT IN ('dismissed','fixed','verified'))   AS open_high,
            COUNT(DISTINCT owner) FILTER (WHERE owner IS NOT NULL
                                           AND status NOT IN ('dismissed','fixed','verified')) AS owners_with_open
        FROM vulnerabilities
        """,
        fetch=True,
    )
    org = org_rows[0] if org_rows else {}

    repos = []
    for r in repo_rows or []:
        repos.append(
            {
                "repo_name": r["repo_name"],
                "total_vulns": int(r["total_vulns"] or 0),
                "open_vulns": int(r["open_vulns"] or 0),
                "open_high": int(r["open_high"] or 0),
                "open_med": int(r["open_med"] or 0),
                "open_low": int(r["open_low"] or 0),
                "regressions": int(r["regressions"] or 0),
                "last_scan": str(r["last_scan"]) if r["last_scan"] else None,
                "total_scans": int(r["total_scans"] or 0),
            }
        )

    return {
        "org": {
            "open_total": int(org.get("open_total") or 0),
            "regressions": int(org.get("regressions") or 0),
            "open_high": int(org.get("open_high") or 0),
            "owners_with_open": int(org.get("owners_with_open") or 0),
            "repo_count": len(repos),
        },
        "repos": repos,
    }


@router.get("/compliance", summary="OWASP Top 10 compliance matrix")
async def compliance_matrix(
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Return open vuln counts bucketed by OWASP Top 10 category."""
    rows = db.execute(
        """
        SELECT canonical_rule_id, COUNT(*) AS n
        FROM vulnerabilities
        WHERE status NOT IN ('dismissed', 'fixed', 'verified')
        GROUP BY canonical_rule_id
        """,
        fetch=True,
    )
    rule_counts: dict[str, int] = {}
    for r in rows or []:
        rule_counts[r["canonical_rule_id"]] = int(r["n"] or 0)

    matrix = []
    for category, rule_prefixes in OWASP_MAP.items():
        count = sum(n for rule, n in rule_counts.items() if any(rule.startswith(p) for p in rule_prefixes))
        matrix.append(
            {
                "category": category,
                "open_count": count,
                "risk": "high" if count >= 5 else "medium" if count >= 1 else "none",
            }
        )

    return {"matrix": matrix, "total_open": sum(r["open_count"] for r in matrix)}


@router.get("/stride/{repo_name}", summary="Auto-STRIDE threat model for a repo")
async def stride_model(
    repo_name: str,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Generate a STRIDE threat model from open vulnerabilities in a repo."""
    rows = db.execute(
        """
        SELECT v.canonical_rule_id, v.severity, v.file_path, v.title, v.short_id
        FROM vulnerabilities v
        JOIN findings f ON f.vulnerability_id = v.id
        JOIN analysis_runs ar ON ar.id = f.run_id
        WHERE ar.repo_name = %s
          AND v.status NOT IN ('dismissed', 'fixed', 'verified')
        GROUP BY v.id
        ORDER BY v.severity
        """,
        (repo_name,),
        fetch=True,
    )

    threats: dict[str, list[dict]] = {k: [] for k in STRIDE_MAP}
    unclassified: list[dict] = []

    for r in rows or []:
        rule = r.get("canonical_rule_id", "")
        matched = False
        for threat, prefixes in STRIDE_MAP.items():
            if any(rule.startswith(p) for p in prefixes):
                threats[threat].append(
                    {
                        "short_id": r["short_id"],
                        "rule": rule,
                        "severity": r["severity"],
                        "file": r["file_path"],
                        "title": r["title"],
                    }
                )
                matched = True
                break
        if not matched:
            unclassified.append({"short_id": r["short_id"], "rule": rule, "severity": r["severity"]})

    return {
        "repo_name": repo_name,
        "stride": [
            {
                "threat": threat,
                "count": len(items),
                "risk": "high" if any(i["severity"] == "high" for i in items) else "medium" if items else "none",
                "vulns": items[:10],
            }
            for threat, items in threats.items()
        ],
        "unclassified_count": len(unclassified),
        "total_open": sum(len(v) for v in threats.values()) + len(unclassified),
    }
