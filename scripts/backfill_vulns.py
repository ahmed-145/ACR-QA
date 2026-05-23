"""One-shot backfill: compute fingerprints for all existing findings and group them
into Vulnerability rows.

Run ONCE after applying migration 0019:
    python scripts/backfill_vulns.py

Safe to re-run: upsert_vulnerability uses ON CONFLICT(fingerprint) DO UPDATE,
and link_finding_to_vulnerability is idempotent.

Prints a summary at the end.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone as _tz
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from CORE.engines.fingerprint import compute_fingerprint
from DATABASE.database import Database


def run() -> None:
    db = Database()

    print("Fetching all findings…")
    rows = db.execute(
        """
        SELECT id, canonical_rule_id, file_path, canonical_severity,
               category, message, evidence, run_id, created_at
        FROM findings
        ORDER BY created_at ASC
        """,
        fetch=True,
    )

    if not rows:
        print("No findings found. Nothing to backfill.")
        return

    print(f"Found {len(rows)} findings. Computing fingerprints…")

    created = 0
    linked = 0
    skipped = 0

    for row in rows:
        try:
            import json as _json

            evidence = row.get("evidence") or {}
            if isinstance(evidence, str):
                try:
                    evidence = _json.loads(evidence)
                except Exception:
                    evidence = {}

            fp = compute_fingerprint(
                canonical_rule_id=row.get("canonical_rule_id") or "UNKNOWN",
                file_path=row.get("file_path") or "",
                evidence=evidence,
                message=row.get("message") or "",
            )

            seen_at = row.get("created_at") or datetime.now(_tz.utc)
            defaults = {
                "canonical_rule_id": row.get("canonical_rule_id") or "UNKNOWN",
                "file_path": row.get("file_path") or "",
                "severity": row.get("canonical_severity") or "low",
                "category": row.get("category"),
                "message": row.get("message"),
                "first_seen_run_id": row.get("run_id"),
                "first_seen_at": seen_at,
                "last_seen_at": seen_at,
            }

            existing = db.get_vulnerability_by_fingerprint(fp)
            vuln = db.upsert_vulnerability(fp, defaults)

            if not existing:
                created += 1

            if vuln and row.get("id"):
                db.link_finding_to_vulnerability(row["id"], vuln["id"])
                linked += 1

        except Exception as exc:
            print(f"  WARNING: skipped finding {row.get('id')}: {exc}")
            skipped += 1

    print(
        f"\nBackfill complete:\n"
        f"  Vulnerabilities created: {created}\n"
        f"  Findings linked:         {linked}\n"
        f"  Findings skipped:        {skipped}"
    )
    db.close()


if __name__ == "__main__":
    run()
