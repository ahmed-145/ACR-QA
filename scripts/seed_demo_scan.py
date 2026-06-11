#!/usr/bin/env python3
"""
Seed the dashboard with a REAL scan so defense-day demos show genuine, defensible
numbers — never fabricated estimates.

Why this exists
---------------
The dashboard reads everything from the database via the API. A fresh database (or
one holding only pytest fixtures) makes every tile render zeros. The honest fix is
not a hard-coded "demo mode" — it is to run an actual scan of the bundled,
intentionally-vulnerable sample app and let the real pipeline populate the database.

Every number the dashboard then shows (Confirmed Tier count, OWASP heatmap, severity
breakdown) traces back to this real scan and is fully reproducible by re-running it.

Important: the sample is copied OUT of ``TESTS/`` first. Findings inside a test path
are deliberately suppressed by the Confirmed-Tier and quality-gate test-path filters,
so scanning ``TESTS/samples/...`` directly would (correctly) yield 0 confirmed findings.
Copying to a non-test path lets the Confirmed Tier populate exactly as it would on a
real production repository.

Usage
-----
    python3 scripts/seed_demo_scan.py
    python3 scripts/seed_demo_scan.py --repo-name my-demo --keep-ai

Requires PostgreSQL to be up (the API's database). Run ``make seed-admin`` first if
you also need a login.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_SRC = PROJECT_ROOT / "TESTS" / "samples" / "comprehensive-issues"
DEMO_DEST = Path("/tmp/acrqa-demo-app")


def stage_sample() -> Path:
    """Copy the bundled vulnerable sample out of TESTS/ to a non-test path."""
    if not SAMPLE_SRC.is_dir():
        sys.exit(f"✗ Sample app not found at {SAMPLE_SRC}")
    if DEMO_DEST.exists():
        shutil.rmtree(DEMO_DEST)
    shutil.copytree(SAMPLE_SRC, DEMO_DEST, ignore=shutil.ignore_patterns("__pycache__"))
    return DEMO_DEST


def run_scan(target: Path, repo_name: str, keep_ai: bool) -> int:
    """Invoke the real CLI pipeline; returns the process exit code.

    ``CORE/main.py`` exits 1 *only* when the quality gate blocks (i.e. it found
    severe findings). For a deliberately-vulnerable demo app that is the expected,
    correct outcome — the scan still completed and seeded the database. So both
    exit 0 (gate passed) and exit 1 (gate blocked) are treated as success; any
    other code signals a genuine error.
    """
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "CORE" / "main.py"),
        "--target-dir",
        str(target),
        "--repo-name",
        repo_name,
    ]
    if not keep_ai:
        cmd.append("--no-ai")  # AI explanations need GROQ keys and add minutes; skip by default
    print(f"▶ Scanning {target} as {repo_name!r} (ai={'on' if keep_ai else 'off'}) …")
    proc = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return proc.returncode


def main() -> None:
    ap = argparse.ArgumentParser(description="Seed the dashboard with a real demo scan.")
    ap.add_argument("--repo-name", default="demo-defense-app", help="Repo label shown in the dashboard")
    ap.add_argument("--keep-ai", action="store_true", help="Run AI explanations too (slower; needs GROQ keys)")
    args = ap.parse_args()

    target = stage_sample()
    code = run_scan(target, args.repo_name, args.keep_ai)
    # 0 = gate passed, 1 = gate blocked (expected for a vulnerable demo). Both seeded ok.
    if code not in (0, 1):
        sys.exit(f"✗ Scan failed with code {code}")
    if code == 1:
        print("\nℹ Quality gate blocked (expected — the demo app is intentionally vulnerable).")

    print(
        "\n✓ Demo scan seeded. Start the API and open the dashboard:\n"
        "    .venv/bin/uvicorn FRONTEND.api.main:app --port 8000\n"
        "  The Overview, run-detail OWASP heatmap, and Analytics now show real numbers\n"
        "  from this scan — Confirmed Tier, severity, and OWASP categories are all live."
    )


if __name__ == "__main__":
    main()
