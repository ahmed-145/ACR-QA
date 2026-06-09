#!/usr/bin/env python3
"""
Scan GoVWA and seed it to the database, backdating it to 4 days ago.
This bridges the gap for Go scans since the Go adapter only outputs JSON files.
"""

from __future__ import annotations

import json
import os
import sys
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from DATABASE.database import Database


def backdate_run(db: Database, run_id: int, days_ago: int) -> None:
    # Compute backdated timestamp
    target_dt = datetime.now(timezone.utc) - timedelta(days=days_ago)

    # Naive timestamp for without time zone columns
    naive_dt = target_dt.replace(tzinfo=None)

    print(f"⌛ Backdating Run ID {run_id} to {days_ago} days ago ({target_dt.strftime('%Y-%m-%d %H:%M:%S')})...")

    # Update analysis_runs
    db.execute(
        "UPDATE analysis_runs SET started_at = %s, completed_at = %s WHERE id = %s",
        (naive_dt, naive_dt, run_id)
    )

    # Update findings
    db.execute(
        "UPDATE findings SET created_at = %s WHERE run_id = %s",
        (naive_dt, run_id)
    )

    # Update vulnerabilities
    db.execute(
        """
        UPDATE vulnerabilities
        SET first_seen_at = %s, last_seen_at = %s, created_at = %s, updated_at = %s
        WHERE first_seen_run_id = %s
        """,
        (target_dt, target_dt, target_dt, target_dt, run_id)
    )
    print(f"✓ Run ID {run_id} backdated successfully.")


def main() -> None:
    db = Database()
    if not db.available():
        print("❌ PostgreSQL database is not available. Please start the DB first.")
        sys.exit(1)

    repo_name = "GoVWA"
    folder_name = "govwa"
    days_ago = 4

    repo_path = PROJECT_ROOT / "test_targets" / "eval-repos" / folder_name
    if not repo_path.exists():
        print(f"❌ GoVWA folder not found at {repo_path}")
        sys.exit(1)

    print(f"🚀 Scanning GoVWA ({folder_name})...")

    # Execute scan via CORE/main.py
    cmd = [
        sys.executable,
        "CORE/main.py",
        "--target-dir", str(repo_path),
        "--repo-name", repo_name,
        "--lang", "go",
        "--no-ai"
    ]

    env = os.environ.copy()
    subprocess.run(cmd, env=env, cwd=str(PROJECT_ROOT))

    # Read findings from DATA/outputs/findings.json
    findings_path = PROJECT_ROOT / "DATA" / "outputs" / "findings.json"
    if not findings_path.exists():
        print("❌ findings.json output not found after scan.")
        sys.exit(1)

    with open(findings_path) as fp:
        findings = json.load(fp)

    print(f"✓ Loaded {len(findings)} findings from {findings_path}")

    # Create the run in DB
    run_id = db.create_analysis_run(repo_name=repo_name)
    print(f"✓ Created database run ID: {run_id} for GoVWA")

    # Insert findings
    inserted_count = 0
    for f in findings:
        try:
            db.insert_finding(run_id, f)
            inserted_count += 1
        except Exception as e:
            print(f"  Warning: failed to insert finding: {e}")

    print(f"✓ Inserted {inserted_count}/{len(findings)} findings into database.")

    # Complete the run
    db.complete_analysis_run(run_id, len(findings))

    # Backdate the run
    backdate_run(db, run_id, days_ago)

    db.close()
    print("\n🎉 GoVWA scan seeded and backdated successfully!")


if __name__ == "__main__":
    main()
