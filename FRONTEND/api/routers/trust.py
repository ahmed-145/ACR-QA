"""Trust — public, no-auth posture endpoints. Phase 6.

All endpoints here are intentionally unauthenticated — designed to be linked
publicly and embedded in README badges. They reveal aggregate counts only;
no specific file paths, rule IDs, or finding details are exposed.

Routes:
  GET /v1/trust/{repo_name}              — posture summary + signed payload
  GET /v1/trust/{repo_name}/attestation  — latest signed ECDSA attestation bundle
  GET /v1/trust/{repo_name}/public-key   — PEM public key for in-browser verification
  GET /v1/trust/badge/{repo_name}        — SVG embeddable badge
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from fastapi import APIRouter, Depends, HTTPException  # noqa: E402
from fastapi.responses import Response  # noqa: E402

from DATABASE.database import Database  # noqa: E402
from FRONTEND.api.deps import get_db  # noqa: E402

router = APIRouter(prefix="/v1/trust", tags=["trust"])

# ── Attestation engine singleton ──────────────────────────────────────────────

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        try:
            from CORE.engines.attestation import AttestationEngine

            _engine = AttestationEngine()
        except Exception:
            _engine = None
    return _engine


# ── Badge SVG generator ───────────────────────────────────────────────────────


def _badge_svg(label: str, message: str, color: str) -> str:
    """Generate a shields.io-style flat badge SVG."""
    label_w = len(label) * 6 + 16
    msg_w = len(message) * 6 + 16
    total_w = label_w + msg_w

    # Color hex map
    colors = {
        "brightgreen": "#4c1",
        "green": "#97ca00",
        "yellow": "#dfb317",
        "red": "#e05d44",
        "lightgrey": "#9f9f9f",
        "blue": "#007ec6",
    }
    fill = colors.get(color, color)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="20">
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r"><rect width="{total_w}" height="20" rx="3" fill="#fff"/></clipPath>
  <g clip-path="url(#r)">
    <rect width="{label_w}" height="20" fill="#555"/>
    <rect x="{label_w}" width="{msg_w}" height="20" fill="{fill}"/>
    <rect width="{total_w}" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="11">
    <text x="{label_w // 2}" y="15" fill="#010101" fill-opacity=".3">{label}</text>
    <text x="{label_w // 2}" y="14">{label}</text>
    <text x="{label_w + msg_w // 2}" y="15" fill="#010101" fill-opacity=".3">{message}</text>
    <text x="{label_w + msg_w // 2}" y="14">{message}</text>
  </g>
</svg>"""


# ── Posture aggregation ───────────────────────────────────────────────────────


def _get_repo_posture(repo_name: str, db: Database) -> dict:
    """Aggregate posture for a repo. Raises 404 if no runs found."""
    run_rows = db.execute(
        """
        SELECT COUNT(*) AS scan_count,
               MAX(started_at) AS last_scan,
               MIN(started_at) AS first_scan,
               SUM(total_findings) AS total_findings_ever
        FROM analysis_runs
        WHERE repo_name = %s AND status = 'completed'
        """,
        (repo_name,),
        fetch=True,
    )
    run_meta = run_rows[0] if run_rows else {}
    scan_count = int(run_meta.get("scan_count") or 0)

    if scan_count == 0:
        raise HTTPException(status_code=404, detail=f"No completed scans found for repo: {repo_name!r}")

    last_scan = run_meta.get("last_scan")
    first_scan = run_meta.get("first_scan")

    # Days since last scan
    freshness_days: int | None = None
    if last_scan:
        try:
            import datetime

            ls = (
                last_scan
                if isinstance(last_scan, datetime.datetime)
                else datetime.datetime.fromisoformat(str(last_scan))
            )
            freshness_days = max(
                0,
                (datetime.datetime.now(datetime.timezone.utc) - ls.replace(tzinfo=datetime.timezone.utc)).days,  # noqa: UP017
            )
        except Exception:
            pass

    # Scan frequency (scans/week over lifetime)
    scan_freq: float | None = None
    if first_scan and last_scan and scan_count > 1:
        try:
            import datetime

            fs = (
                first_scan
                if isinstance(first_scan, datetime.datetime)
                else datetime.datetime.fromisoformat(str(first_scan))
            )
            ls2 = (
                last_scan
                if isinstance(last_scan, datetime.datetime)
                else datetime.datetime.fromisoformat(str(last_scan))
            )
            span_weeks = max(1, ((ls2 - fs).total_seconds()) / (7 * 86400))
            scan_freq = round(scan_count / span_weeks, 2)
        except Exception:
            pass

    # Open vuln counts (aggregate only — no file paths or rule IDs exposed)
    vuln_rows = db.execute(
        """
        SELECT
            COUNT(v.id) FILTER (WHERE v.status NOT IN ('dismissed','fixed','verified')) AS open_total,
            COUNT(v.id) FILTER (WHERE v.severity = 'high'
                                  AND v.status NOT IN ('dismissed','fixed','verified'))   AS open_high,
            COUNT(v.id) FILTER (WHERE v.severity = 'medium'
                                  AND v.status NOT IN ('dismissed','fixed','verified'))   AS open_med,
            COUNT(v.id) FILTER (WHERE v.severity = 'low'
                                  AND v.status NOT IN ('dismissed','fixed','verified'))   AS open_low,
            COUNT(v.id) FILTER (WHERE v.status = 'fixed')                                AS fixed_total,
            COUNT(v.id) FILTER (WHERE v.status = 'regressed')                            AS regressions
        FROM vulnerabilities v
        JOIN findings f ON f.vulnerability_id = v.id
        JOIN analysis_runs ar ON ar.id = f.run_id
        WHERE ar.repo_name = %s
        GROUP BY ar.repo_name
        """,
        (repo_name,),
        fetch=True,
    )
    vuln = vuln_rows[0] if vuln_rows else {}

    open_high = int(vuln.get("open_high") or 0)
    open_med = int(vuln.get("open_med") or 0)
    open_low = int(vuln.get("open_low") or 0)
    open_total = int(vuln.get("open_total") or 0)
    fixed_total = int(vuln.get("fixed_total") or 0)
    regressions = int(vuln.get("regressions") or 0)

    # Compliance status
    owasp_status = "pass" if open_high == 0 else "fail"
    cwe_status = "pass" if open_high == 0 and open_med <= 2 else ("warn" if open_high == 0 else "fail")
    overall = "fail" if open_high > 0 else ("warn" if open_med > 0 else "pass")

    posture = {
        "repo_name": repo_name,
        "scan_count": scan_count,
        "last_scan": str(last_scan) if last_scan else None,
        "first_scan": str(first_scan) if first_scan else None,
        "freshness_days": freshness_days,
        "scan_frequency_per_week": scan_freq,
        "open_total": open_total,
        "open_high": open_high,
        "open_med": open_med,
        "open_low": open_low,
        "fixed_total": fixed_total,
        "regressions": regressions,
        "compliance": {
            "owasp_top10": owasp_status,
            "cwe_top25": cwe_status,
            "overall": overall,
        },
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    return posture


# ── Routes ────────────────────────────────────────────────────────────────────


@router.get("/{repo_name}", summary="Public posture summary — no auth required")
async def trust_posture(
    repo_name: str,
    db: Database = Depends(get_db),
):
    """Return aggregate posture for a repo. No specific vuln details exposed.

    Response includes an ECDSA-P256 signature over the canonical JSON so
    consumers can verify the payload hasn't been tampered with using the
    public key at GET /v1/trust/{repo_name}/public-key.
    """
    posture = _get_repo_posture(repo_name, db)

    # Sign the posture payload
    signature: dict | None = None
    engine = _get_engine()
    if engine:
        try:
            canonical = json.dumps(posture, sort_keys=True, separators=(",", ":")).encode()
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import ec

            raw_sig = engine._key.sign(canonical, ec.ECDSA(hashes.SHA256()))
            signature = {
                "algorithm": "ECDSA-P256",
                "signature": raw_sig.hex(),
                "key_id": engine._kid,
            }
        except Exception:
            pass

    return {
        **posture,
        "signature": signature,
        "public_key_url": f"/v1/trust/{repo_name}/public-key",
        "attestation_url": f"/v1/trust/{repo_name}/attestation",
    }


@router.get("/{repo_name}/attestation", summary="Latest signed ECDSA attestation bundle — no auth")
async def trust_attestation(
    repo_name: str,
    db: Database = Depends(get_db),
):
    """Return the most recent ECDSA-signed attestation for the latest run."""
    run_rows = db.execute(
        "SELECT id FROM analysis_runs WHERE repo_name = %s AND status = 'completed' ORDER BY started_at DESC LIMIT 1",
        (repo_name,),
        fetch=True,
    )
    if not run_rows:
        raise HTTPException(status_code=404, detail=f"No completed runs for {repo_name!r}")

    run_id = run_rows[0]["id"]
    att = db.get_attestation(run_id)
    if not att:
        raise HTTPException(status_code=404, detail=f"No attestation recorded for latest run of {repo_name!r}")

    # Parse the stored JSON
    try:
        bundle = json.loads(att["attestation_json"])
    except Exception:
        bundle = {"raw": att["attestation_json"]}

    return {
        "run_id": run_id,
        "repo_name": repo_name,
        "key_id": att.get("key_id"),
        "created_at": str(att.get("created_at")) if att.get("created_at") else None,
        "bundle": bundle,
        "signature": att.get("signature"),
        "public_key_url": f"/v1/trust/{repo_name}/public-key",
    }


@router.get("/{repo_name}/public-key", summary="PEM public key for in-browser ECDSA verification — no auth")
async def trust_public_key(
    repo_name: str,
):
    """Return PEM-encoded ECDSA-P256 public key.

    Consumers can use this with WebCrypto `subtle.verify` to independently
    verify the signatures in the posture and attestation endpoints without
    trusting the server.
    """
    engine = _get_engine()
    if not engine:
        raise HTTPException(status_code=503, detail="Attestation engine unavailable")

    pem = engine.public_key_pem()
    # Also expose key_id and DER fingerprint for pinning
    from CORE.engines.attestation import _key_id

    kid = _key_id(engine._key)

    return Response(
        content=json.dumps({"kid": kid, "algorithm": "ECDSA-P256", "pem": pem}),
        media_type="application/json",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/badge/{repo_name}", summary="SVG embeddable security badge — no auth")
async def trust_badge(
    repo_name: str,
    db: Database = Depends(get_db),
):
    """Return shields.io-style SVG badge.

    Embed in README:
      ![security status](https://your-host/v1/trust/badge/{repo_name})
    """
    try:
        posture = _get_repo_posture(repo_name, db)
    except HTTPException:
        svg = _badge_svg("security", "not scanned", "lightgrey")
        return Response(content=svg, media_type="image/svg+xml", headers={"Cache-Control": "no-cache"})

    freshness = posture.get("freshness_days")
    stale = freshness is not None and freshness > 30

    if stale:
        svg = _badge_svg("security", "stale", "yellow")
    elif posture["open_high"] > 0:
        n = posture["open_high"]
        svg = _badge_svg("security", f"{n} critical", "red")
    elif posture["open_med"] > 0:
        n = posture["open_med"]
        svg = _badge_svg("security", f"{n} medium", "yellow")
    elif posture["open_total"] == 0:
        svg = _badge_svg("security", "passing", "brightgreen")
    else:
        svg = _badge_svg("security", f"{posture['open_low']} low", "green")

    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={"Cache-Control": "no-cache, no-store"},
    )
