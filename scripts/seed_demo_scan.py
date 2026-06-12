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
SAMPLES_DIR = PROJECT_ROOT / "TESTS" / "samples"
STAGING = Path("/tmp/acrqa-demo")

# Curated demo apps: (sample-dir, dashboard repo name). Honest, descriptive names —
# each is a sample application with intentionally-planted vulnerabilities (the same
# kind used in security training). The tool's detection on them is real.
DEMO_APPS = [
    ("comprehensive-issues", "payments-api"),
    ("realistic-issues", "web-backend"),
    ("seeded-repo", "internal-tools"),
]


def stage_sample(sample_name: str) -> Path:
    """Copy a bundled vulnerable sample out of TESTS/ to a non-test path.

    Findings inside a test path are deliberately suppressed by the Confirmed-Tier and
    quality-gate test-path filters, so the sample must be scanned from outside TESTS/.
    """
    src = SAMPLES_DIR / sample_name
    if not src.is_dir():
        sys.exit(f"✗ Sample app not found at {src}")
    dest = STAGING / sample_name
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__"))
    return dest


def reset_repos(repo_names: list[str]) -> None:
    """Delete existing runs for the given repo names (findings cascade via FK).

    Keeps re-seeding idempotent — without this, every run of the script piles up a
    fresh duplicate run per app. Only touches the named demo repos; never the real
    evaluation/benchmark repos.
    """
    sys.path.insert(0, str(PROJECT_ROOT))
    from DATABASE.database import Database  # noqa: PLC0415

    db = Database()
    if not db.available():
        print("⚠ Database unavailable — skipping reset.")
        return
    for name in repo_names:
        db.execute("DELETE FROM analysis_runs WHERE repo_name = %s", (name,))
    print(f"🧹 Reset prior runs for: {', '.join(repo_names)}")


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
    ap = argparse.ArgumentParser(description="Seed the dashboard with real demo scans.")
    ap.add_argument(
        "--sample",
        help="Scan a single TESTS/samples/<dir> as the given --repo-name (default: seed all curated apps)",
    )
    ap.add_argument("--repo-name", help="Repo label (only with --sample)")
    ap.add_argument("--keep-ai", action="store_true", help="Run AI explanations too (slower; needs GROQ keys)")
    ap.add_argument(
        "--reset",
        action="store_true",
        help="Delete prior runs for the demo repos first (idempotent re-seed; never touches real repos)",
    )
    args = ap.parse_args()

    if args.sample:
        apps = [(args.sample, args.repo_name or args.sample)]
    else:
        apps = DEMO_APPS

    if args.reset:
        reset_repos([repo for _, repo in apps])

    seeded = 0
    for sample_name, repo_name in apps:
        target = stage_sample(sample_name)
        code = run_scan(target, repo_name, args.keep_ai)
        # 0 = gate passed, 1 = gate blocked (expected for a vulnerable app). Both seeded ok.
        if code not in (0, 1):
            print(f"⚠ {repo_name}: scan failed with code {code} — skipping")
            continue
        seeded += 1
        if code == 1:
            print(f"ℹ {repo_name}: quality gate blocked (expected — intentionally vulnerable).\n")

    if seeded == 0:
        sys.exit("✗ No apps seeded.")

    print(
        f"\n✓ Seeded {seeded} demo app(s). Start the API and open the dashboard:\n"
        "    .venv/bin/uvicorn FRONTEND.api.main:app --port 8000\n"
        "  Overview, run-detail OWASP heatmap, Fleet, and Analytics now show real numbers\n"
        "  from these scans — Confirmed Tier, severity, and OWASP categories are all live."
    )


if __name__ == "__main__":
    main()
