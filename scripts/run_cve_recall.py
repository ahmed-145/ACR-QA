#!/usr/bin/env python3
"""
run_cve_recall.py — Tier 1 CVE Recall harness.

For each CVE YAML in TESTS/evaluation/cve_recall/:
  1. Clones the project at vuln_commit_sha into TESTS/evaluation/cloned/cve_recall/<cve_id>/
  2. Runs ACR-QA (--no-ai --json) against the cloned repo
  3. Applies the strict ±3-line scoring rule from INTEGRITY.md
  4. Updates the YAML with acrqa_detected + acrqa_finding_id
  5. Prints a summary table

Pre-registration check: enforces that each CVE YAML has a pre_registered_sha
field, meaning it was committed before the scan was run.

Usage:
    python3 scripts/run_cve_recall.py [--cve CVE-XXXX-XXXXX] [--dry-run]

Flags:
    --cve        Run a single CVE by ID (default: all)
    --dry-run    Clone + show planned scan but don't run ACR-QA
    --no-clone   Skip cloning (use existing cloned/ directory)
    --update     Write scan results back into YAML files
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
CVE_DIR = ROOT / "TESTS" / "evaluation" / "cve_recall"
CLONE_BASE = ROOT / "TESTS" / "evaluation" / "cloned" / "cve_recall"
RUN_CHECKS_SH = ROOT / "TOOLS" / "run_checks.sh"

# Add project root to sys.path so CORE imports work
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"

TOLERANCE_LINES = 3  # ±3 lines — from INTEGRITY.md scoring rule


# ---------------------------------------------------------------------------
# YAML loading
# ---------------------------------------------------------------------------


def load_cve_yamls(cve_filter: str | None = None) -> list[dict]:
    yamls = sorted(CVE_DIR.glob("*.yml"))
    if cve_filter:
        yamls = [y for y in yamls if cve_filter.lower() in y.stem.lower()]
    if not yamls:
        print(f"{YELLOW}No CVE YAMLs found in {CVE_DIR}{RESET}")
        return []
    result = []
    for path in yamls:
        with path.open() as f:
            data = yaml.safe_load(f)
        data["_path"] = path
        result.append(data)
    return result


# ---------------------------------------------------------------------------
# Pre-registration check
# ---------------------------------------------------------------------------


def check_pre_registration(cve: dict) -> bool:
    """Verify pre_registered_sha is present (committed before scanning)."""
    sha = cve.get("pre_registered_sha", "").strip()
    if not sha or sha.startswith("<"):
        print(f"  {RED}✗ pre_registered_sha missing for {cve['cve_id']} — " f"must commit YAML before scanning{RESET}")
        return False
    return True


# ---------------------------------------------------------------------------
# Cloning
# ---------------------------------------------------------------------------


def clone_repo(cve: dict, no_clone: bool = False) -> Path | None:
    cve_id = cve["cve_id"]
    vuln_sha = cve.get("vuln_commit_sha", "").strip()
    vuln_tag = cve.get("vuln_version_tag", "").strip()
    url = cve.get("repo_url", "").strip()
    clone_dir = CLONE_BASE / cve_id

    # Determine checkout ref: prefer explicit SHA, fall back to version tag
    checkout_ref = vuln_sha if (vuln_sha and not vuln_sha.startswith("<")) else vuln_tag

    if no_clone and clone_dir.exists():
        print(f"  Using existing clone: {clone_dir}")
        return clone_dir

    if not url or url.startswith("<"):
        print(f"  {YELLOW}⚠  repo_url not set for {cve_id} — skipping clone{RESET}")
        return None

    if not checkout_ref:
        print(f"  {YELLOW}⚠  neither vuln_commit_sha nor vuln_version_tag set " f"for {cve_id} — skipping clone{RESET}")
        return None

    CLONE_BASE.mkdir(parents=True, exist_ok=True)

    if clone_dir.exists():
        print(f"  Repo already cloned at {clone_dir} — checking out {checkout_ref}")
        r = subprocess.run(["git", "checkout", checkout_ref], cwd=clone_dir, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"  {RED}git checkout {checkout_ref} failed: {r.stderr.strip()}{RESET}")
            return None
        return clone_dir

    # Clone at specific tag (depth=1 is enough for a tagged release)
    clone_cmd = (
        ["git", "clone", "--branch", checkout_ref, "--depth=1", url, str(clone_dir)]
        if vuln_tag and not vuln_sha
        else ["git", "clone", "--no-checkout", "--depth=50", url, str(clone_dir)]
    )
    print(f"  Cloning {url} @ {checkout_ref} ...")
    r = subprocess.run(clone_cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  {RED}Clone failed: {r.stderr.strip()}{RESET}")
        return None

    if not vuln_tag or vuln_sha:
        # Need explicit checkout for commit SHA clones
        r = subprocess.run(["git", "checkout", vuln_sha], cwd=clone_dir, capture_output=True, text=True)
        if r.returncode != 0:
            # Fallback: fetch then checkout
            subprocess.run(["git", "fetch", "--unshallow"], cwd=clone_dir, capture_output=True)
            r = subprocess.run(["git", "checkout", checkout_ref], cwd=clone_dir, capture_output=True, text=True)
            if r.returncode != 0:
                print(f"  {RED}Checkout {checkout_ref} failed: {r.stderr.strip()}{RESET}")
                return None

    print(f"  {GREEN}Cloned at {checkout_ref}{RESET}")
    return clone_dir


# ---------------------------------------------------------------------------
# ACR-QA scan — runs tools directly, no DB required
# ---------------------------------------------------------------------------


def run_acrqa(clone_dir: Path) -> list[dict]:
    """
    Run static analysis tools on clone_dir via TOOLS/run_checks.sh,
    then normalise via CORE.engines.normalizer.normalize_all().
    No DB connection required.
    """

    # run_checks.sh hardcodes DATA/outputs — run sequentially
    out_dir = ROOT / "DATA" / "outputs"
    r = subprocess.run(
        ["bash", str(RUN_CHECKS_SH), str(clone_dir)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=300,
    )
    if r.returncode not in (0, 1):
        print(f"  {YELLOW}run_checks.sh returned {r.returncode}: " f"{r.stderr.strip()[:200]}{RESET}")

    # Normalise outputs from DATA/outputs/
    try:
        from CORE.engines.normalizer import normalize_all

        findings = normalize_all(str(out_dir))
        return [
            {
                "canonical_id": getattr(f, "canonical_rule_id", None),
                "severity": getattr(f, "severity", "unknown"),
                "file_path": getattr(f, "file", None),
                "line_number": getattr(f, "line", None),
                "message": getattr(f, "message", ""),
                "tool": getattr(f, "tool_raw", {}).get("tool_name", "")
                if isinstance(getattr(f, "tool_raw", None), dict)
                else "",
            }
            for f in findings
        ]
    except Exception as exc:
        print(f"  {YELLOW}normalize_all failed: {exc}{RESET}")
        return []


# ---------------------------------------------------------------------------
# Scoring — strict ±3-line rule from INTEGRITY.md
# ---------------------------------------------------------------------------


def score_cve(cve: dict, findings: list[dict]) -> tuple[bool, str | None]:
    """
    Return (detected, matching_finding_id).
    Detected = HIGH severity finding within ±3 lines of any affected_line.
    """
    affected_file = cve.get("affected_file", "")
    affected_lines: list[int] = cve.get("affected_lines", [])

    if not affected_lines:
        return False, None

    # Normalise affected_file to just the filename parts for fuzzy matching
    affected_file_parts = Path(affected_file).parts

    for f in findings:
        severity = (f.get("severity") or "").lower()
        if severity != "high":
            continue

        f_file = f.get("file_path") or f.get("file") or ""
        f_line = f.get("line_number") or f.get("line") or 0
        try:
            f_line = int(f_line)
        except (ValueError, TypeError):
            continue

        # File match: check if affected_file is a suffix of the finding's file
        f_parts = Path(f_file).parts
        file_match = (
            affected_file_parts[-1] == f_parts[-1]  # same filename
            and (len(affected_file_parts) == 1 or f_file.endswith(affected_file) or affected_file.endswith(f_file))
        )

        if not file_match:
            continue

        # Line match: any affected_line within ±3
        for target_line in affected_lines:
            if abs(f_line - target_line) <= TOLERANCE_LINES:
                finding_id = f.get("canonical_id") or f.get("rule_id") or "unknown"
                return True, finding_id

    return False, None


# ---------------------------------------------------------------------------
# YAML update
# ---------------------------------------------------------------------------


def update_yaml(cve: dict, detected: bool, finding_id: str | None) -> None:
    path: Path = cve["_path"]
    with path.open() as f:
        raw = f.read()

    # Replace or append acrqa_detected
    import re

    if re.search(r"^acrqa_detected:", raw, re.MULTILINE):
        raw = re.sub(r"^acrqa_detected:.*$", f"acrqa_detected: {str(detected).lower()}", raw, flags=re.MULTILINE)
    else:
        raw = raw.rstrip() + f"\nacrqa_detected: {str(detected).lower()}\n"

    if finding_id:
        if re.search(r"^acrqa_finding_id:", raw, re.MULTILINE):
            raw = re.sub(r"^acrqa_finding_id:.*$", f"acrqa_finding_id: {finding_id}", raw, flags=re.MULTILINE)
        else:
            raw = raw.rstrip() + f"\nacrqa_finding_id: {finding_id}\n"

    with path.open("w") as f:
        f.write(raw)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cve", help="Run a single CVE by ID")
    parser.add_argument("--dry-run", action="store_true", help="Show plan but don't scan")
    parser.add_argument("--no-clone", action="store_true", help="Skip cloning, use existing directories")
    parser.add_argument("--update", action="store_true", help="Write scan results back into YAML files")
    args = parser.parse_args()

    cves = load_cve_yamls(args.cve)
    if not cves:
        sys.exit(0)

    print(f"\n{BOLD}ACR-QA CVE Recall Pilot{RESET}")
    print("=" * 60)
    print(f"CVEs to test: {len(cves)}")
    print(f"Scoring rule: HIGH severity within ±{TOLERANCE_LINES} lines\n")

    results: list[dict] = []

    for cve in cves:
        cve_id = cve["cve_id"]
        project = cve.get("project", "unknown")
        print(f"{BOLD}── {cve_id} ({project}){RESET}")

        # Pre-registration gate
        if not check_pre_registration(cve):
            results.append({"cve_id": cve_id, "status": "skip_no_prereg"})
            continue

        # Check if a clone ref is available (SHA or version tag)
        vuln_sha = cve.get("vuln_commit_sha", "").strip()
        vuln_tag = cve.get("vuln_version_tag", "").strip()
        checkout_ref = vuln_sha if (vuln_sha and not vuln_sha.startswith("<")) else vuln_tag
        if not checkout_ref:
            print(f"  {YELLOW}⚠  no vuln_commit_sha or vuln_version_tag — marking as pending{RESET}")
            results.append({"cve_id": cve_id, "status": "pending_sha"})
            continue

        if args.dry_run:
            print(
                f"  [dry-run] Would clone {cve.get('repo_url', '?')} "
                f"@ {checkout_ref} and scan {cve.get('affected_file', '?')}"
            )
            results.append({"cve_id": cve_id, "status": "dry_run"})
            continue

        # Clone
        clone_dir = clone_repo(cve, no_clone=args.no_clone)
        if not clone_dir:
            results.append({"cve_id": cve_id, "status": "clone_failed"})
            continue

        # Scan
        print(f"  Running ACR-QA on {clone_dir.name} ...")
        findings = run_acrqa(clone_dir)
        print(f"  Found {len(findings)} findings total")

        # Score
        detected, finding_id = score_cve(cve, findings)
        mark = f"{GREEN}✓ DETECTED{RESET}" if detected else f"{RED}✗ MISSED{RESET}"
        print(f"  {mark}  {f'({finding_id})' if finding_id else ''}")

        if args.update:
            update_yaml(cve, detected, finding_id)
            print(f"  Updated {cve['_path'].name}")

        results.append(
            {
                "cve_id": cve_id,
                "project": project,
                "detected": detected,
                "finding_id": finding_id,
                "total_findings": len(findings),
            }
        )
        print()

    # Summary
    print("=" * 60)
    completed = [r for r in results if "detected" in r]
    if completed:
        detected_count = sum(1 for r in completed if r["detected"])
        print(
            f"\n{BOLD}Recall: {detected_count}/{len(completed)} CVEs detected "
            f"({100*detected_count//max(len(completed),1)}%){RESET}"
        )
        print()
        for r in completed:
            mark = f"{GREEN}✓{RESET}" if r["detected"] else f"{RED}✗{RESET}"
            fid = f" [{r['finding_id']}]" if r.get("finding_id") else ""
            print(f"  {mark}  {r['cve_id']} ({r['project']}){fid}")

    skipped = [r for r in results if r.get("status") in ("pending_sha", "clone_failed")]
    if skipped:
        print(f"\n{YELLOW}{len(skipped)} CVE(s) skipped " f"(commit SHA not yet set or clone failed){RESET}")
        print("  Run again with --update after setting vuln_commit_sha in each YAML.")


if __name__ == "__main__":
    main()
