#!/usr/bin/env python3
"""
Seed evaluation scans in the database and backdate them across the last 7 days.
This populates the dashboard with actual thesis evaluation repos (Layer A)
and spreads them out to show realistic scan history/activity.
"""

from __future__ import annotations

import os
import sys
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from DATABASE.database import Database


# List of evaluation repos to scan and seed (repo_name, folder_name, days_ago)
EVAL_REPOS = [
    ("Bandit-Test-Cases", "bandit-test-cases", 7),
    ("Vulnerable-Flask-App", "vulnerable-flask-app", 7),
    ("NodeGoat", "nodegoat", 6),
    ("DVNA", "dvna", 6),
    ("DVWS-Node", "dvws-node", 5),
    ("JuiceShop", "juiceshop", 5),
    ("Django-NV", "django-nv", 4),
    ("GoVWA", "govwa", 4),
    ("Vulnerable-Node", "vulnerable-node", 3),
    ("DVPWA", "dvpwa", 2),
    ("Pygoat", "pygoat", 1),
    ("VulPy", "vulpy", 1),
    ("DSVW", "dsvw", 0),
]


def clean_database(db: Database) -> None:
    print("🧹 Cleaning existing dashboard mock data...")
    tables = [
        "findings",
        "vulnerabilities",
        "analysis_runs",
        "llm_explanations",
        "scan_attestations",
        "file_risk_scores",
        "pr_risk_scores",
        "finding_history",
        "finding_embeddings",
        "dependency_findings",
        "run_sboms",
    ]
    # We use TRUNCATE CASCADE to clean all related tables cleanly
    table_list = ", ".join(tables)
    db.execute(f"TRUNCATE TABLE {table_list} CASCADE")
    print("✓ Database cleaned successfully.")


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

    # Step 1: Clean the database
    clean_database(db)

    # Step 2: Loop and scan each repo
    for repo_name, folder_name, days_ago in EVAL_REPOS:
        repo_path = PROJECT_ROOT / "test_targets" / "eval-repos" / folder_name
        if not repo_path.exists():
            print(f"\n⚠️  Skipping {repo_name} — folder not found at {repo_path}")
            continue

        print(f"\n==================================================")
        print(f"🚀 Scanning {repo_name} ({folder_name})")
        print(f"==================================================")

        # Execute scan via CORE/main.py
        # We run with --no-ai to avoid making costly LLM API calls and keep it fast
        cmd = [
            sys.executable,
            "CORE/main.py",
            "--target-dir", str(repo_path),
            "--repo-name", repo_name,
            "--lang", "auto",
            "--no-ai"
        ]

        # Run CLI scan
        env = os.environ.copy()
        result = subprocess.run(cmd, env=env, cwd=str(PROJECT_ROOT))

        # Note: CORE/main.py exits with 1 when quality gate fails, but the scan still stores results.
        # So exit code 1 is expected and fine as long as run is registered.

        # Fetch the latest run ID created for this repo
        latest_run = db.execute(
            "SELECT id FROM analysis_runs WHERE repo_name = %s ORDER BY id DESC LIMIT 1",
            (repo_name,),
            fetch=True
        )

        if latest_run:
            run_id = latest_run[0]["id"]
            backdate_run(db, run_id, days_ago)
        else:
            print(f"❌ Failed to find run ID in database for {repo_name} after scan.")

    db.close()
    print("\n🎉 Seeding and backdating evaluation scans completed successfully!")


if __name__ == "__main__":
    main()
