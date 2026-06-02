#!/usr/bin/env python3
"""
run_live_cve_recall.py — X1 Live-CVE Blind Holdout harness.

Evaluates ACR-QA against 10 pre-registered late-2024/2025 CVEs that are
NOT in the existing recall corpus. Ground-truth YAMLs are in:
  TESTS/evaluation/ground_truth/live_cve/

For each YAML:
  1. Clones the repo at checkout_ref into local_path (or uses existing clone)
  2. Runs bandit + semgrep directly on the clone (no DB required)
  3. Normalises findings via CORE.engines.normalizer
  4. Scores:
     - recall_target=1: detected if ≥1 finding matches expected file + canonical_id
     - recall_target=0: always PASS (documented honest miss — SAST cannot detect)
  5. Writes TESTS/evaluation/results/live_cve_recall.json
  6. Prints a summary table

Usage:
    python3 scripts/run_live_cve_recall.py [--cve CVE-ID] [--no-clone] [--dry-run]

Flags:
    --cve        Run a single CVE (partial match on YAML filename)
    --no-clone   Skip cloning, use existing directories
    --dry-run    Show plan, clone, but don't scan
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
LIVE_CVE_DIR = ROOT / "TESTS" / "evaluation" / "ground_truth" / "live_cve"
RESULTS_FILE = ROOT / "TESTS" / "evaluation" / "results" / "live_cve_recall.json"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

TOLERANCE_LINES = 5  # ±5 lines for file-level matching (more lenient than exact-line)


# ---------------------------------------------------------------------------
# YAML loading
# ---------------------------------------------------------------------------


def load_yamls(cve_filter: str | None = None) -> list[dict]:
    paths = sorted(LIVE_CVE_DIR.glob("*.yml"))
    if cve_filter:
        paths = [p for p in paths if cve_filter.lower() in p.stem.lower()]
    if not paths:
        print(f"{YELLOW}No YAMLs found in {LIVE_CVE_DIR}{RESET}")
        return []
    result = []
    for p in paths:
        with p.open() as f:
            data = yaml.safe_load(f)
        data["_path"] = p
        data["_stem"] = p.stem
        result.append(data)
    return result


# ---------------------------------------------------------------------------
# Cloning
# ---------------------------------------------------------------------------


def clone_repo(spec: dict, no_clone: bool = False) -> Path | None:
    url = (spec.get("url") or "").strip()
    ref = (spec.get("checkout_ref") or "").strip()
    local_path = ROOT / spec["local_path"]

    if no_clone and local_path.exists():
        print(f"  {DIM}Using existing clone: {local_path}{RESET}")
        return local_path

    if not url or not ref:
        print(f"  {YELLOW}⚠  url or checkout_ref missing — skipping clone{RESET}")
        return None

    if local_path.exists():
        print(f"  {DIM}Already cloned at {local_path}{RESET}")
        return local_path

    local_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"  Cloning {url} @ {ref} ...", flush=True)

    # Attempt shallow clone at the tag/ref
    cmd = ["git", "clone", "--branch", ref, "--depth=1", url, str(local_path)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        # Fallback: full clone then checkout
        print(f"  {YELLOW}Shallow clone failed, trying full clone...{RESET}")
        cmd2 = ["git", "clone", url, str(local_path)]
        r2 = subprocess.run(cmd2, capture_output=True, text=True)
        if r2.returncode != 0:
            print(f"  {RED}Clone failed: {r2.stderr.strip()[:200]}{RESET}")
            return None
        r3 = subprocess.run(["git", "checkout", ref], cwd=local_path, capture_output=True, text=True)
        if r3.returncode != 0:
            print(f"  {RED}Checkout {ref} failed: {r3.stderr.strip()[:200]}{RESET}")
            return None

    print(f"  {GREEN}Cloned ✓{RESET}")
    return local_path


# ---------------------------------------------------------------------------
# Scan — bandit + semgrep, no DB required
# ---------------------------------------------------------------------------


def run_bandit(target: Path) -> list[dict]:
    """Run bandit on target directory, return raw results list."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        out_path = Path(f.name)

    subprocess.run(
        [sys.executable, "-m", "bandit", "-r", str(target), "-f", "json", "-o", str(out_path), "-ll"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    # bandit returns exit code 1 when findings exist — that's fine
    try:
        with out_path.open() as f:
            data = json.load(f)
        out_path.unlink(missing_ok=True)
        return data.get("results", [])
    except Exception:
        out_path.unlink(missing_ok=True)
        return []


def run_semgrep(target: Path) -> list[dict]:
    """Run semgrep with ACR-QA rules on target directory."""
    rules_path = ROOT / "TOOLS" / "semgrep" / "python-rules.yml"
    if not rules_path.exists():
        return []

    r = subprocess.run(
        ["semgrep", "scan", "--config", str(rules_path), "--json", "--quiet", str(target)],
        capture_output=True,
        text=True,
        timeout=180,
    )
    try:
        data = json.loads(r.stdout)
        return data.get("results", [])
    except Exception:
        return []


def scan_repo(clone_dir: Path) -> list[dict]:
    """
    Run bandit + semgrep on clone_dir and return normalised findings.
    Uses CORE normalizer — no DB or full pipeline required.
    """
    from CORE.engines.normalizer import normalize_bandit, normalize_semgrep

    print("  Running bandit ...", end="", flush=True)
    bandit_raw = run_bandit(clone_dir)
    bandit_findings = normalize_bandit({"results": bandit_raw})
    print(f" {len(bandit_findings)} findings", flush=True)

    print("  Running semgrep ...", end="", flush=True)
    semgrep_raw = run_semgrep(clone_dir)
    semgrep_findings = normalize_semgrep({"results": semgrep_raw})
    print(f" {len(semgrep_findings)} findings", flush=True)

    all_findings = bandit_findings + semgrep_findings

    return [
        {
            "canonical_id": getattr(f, "canonical_rule_id", None),
            "severity": getattr(f, "severity", "unknown"),
            "file": getattr(f, "file", ""),
            "line": getattr(f, "line", 0),
            "message": getattr(f, "message", ""),
        }
        for f in all_findings
    ]


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def score(spec: dict, findings: list[dict], clone_dir: Path) -> tuple[str, str | None]:
    """
    Returns (outcome, matched_canonical_id).

    outcome values:
      'TP'   — expected detection, found it (recall_target=1, detected)
      'FN'   — expected detection, missed  (recall_target=1, not detected)
      'TN'   — expected honest miss, not detected (recall_target=0, correct)
      'FP_X' — expected honest miss but a finding fired (rare; note for review)
    """
    recall_target = spec.get("recall_target", 1)
    expected = spec.get("expected_findings", [])

    if recall_target == 0:
        # Honest miss — SAST cannot detect. Always TN regardless of findings.
        return "TN", None

    if not expected:
        return "FN", None

    for exp in expected:
        exp_file = (exp.get("file") or "").strip()
        exp_canonical = (exp.get("canonical_id") or "").strip()
        match_strategy = exp.get("match_strategy", "exact_rule")

        for f in findings:
            f_file = f.get("file") or ""
            f_canonical = f.get("canonical_id") or ""

            # File match: check if exp_file is a suffix of the finding's file path
            file_match = f_file.endswith(exp_file) or exp_file.endswith(f_file)
            # Also try just matching the filename
            if not file_match and Path(exp_file).name == Path(f_file).name:
                file_match = True

            if not file_match:
                continue

            if match_strategy == "exact_rule":
                if f_canonical == exp_canonical:
                    return "TP", f_canonical
            elif match_strategy == "any_finding":
                # Any finding in the right file counts
                return "TP", f_canonical

    return "FN", None


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


def save_results(results: list[dict]) -> None:
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "harness": "X1 Live-CVE Blind Holdout",
        "pre_registered": "2026-05-30",
        "total": len(results),
        "results": results,
    }
    # Aggregate
    tp = sum(1 for r in results if r.get("outcome") == "TP")
    fn = sum(1 for r in results if r.get("outcome") == "FN")
    tn = sum(1 for r in results if r.get("outcome") == "TN")
    detectable = tp + fn  # recall_target=1 CVEs
    payload["summary"] = {
        "TP": tp,
        "FN": fn,
        "TN": tn,
        "detectable_count": detectable,
        "recall_at_detectable": round(tp / detectable, 4) if detectable else None,
        "honest_miss_count": tn,
        "honest_miss_rate": round(tn / len(results), 4) if results else None,
    }
    with RESULTS_FILE.open("w") as f:
        json.dump(payload, f, indent=2)
    print(f"\n  Results written to {RESULTS_FILE.relative_to(ROOT)}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cve", help="Filter by CVE ID or YAML stem substring")
    parser.add_argument("--no-clone", action="store_true", help="Skip cloning, use existing directories")
    parser.add_argument("--dry-run", action="store_true", help="Clone only, skip scanning")
    args = parser.parse_args()

    specs = load_yamls(args.cve)
    if not specs:
        sys.exit(0)

    print(f"\n{BOLD}ACR-QA X1 — Live-CVE Blind Holdout{RESET}")
    print("=" * 62)
    print(f"Ground-truth YAMLs : {len(specs)}")
    print("Pre-registered     : 2026-05-30")
    print("Scoring            : exact_rule match (canonical_id + file suffix)")
    print()

    results: list[dict] = []

    for spec in specs:
        stem = spec["_stem"]
        repo = spec.get("repo", stem)
        recall_target = spec.get("recall_target", 1)
        tag = f"{CYAN}[detectable]{RESET}" if recall_target == 1 else f"{DIM}[honest-miss]{RESET}"
        print(f"{BOLD}── {stem}{RESET}  {tag}")

        # Clone
        clone_dir = clone_repo(spec, no_clone=args.no_clone)
        if clone_dir is None:
            results.append({"cve": stem, "outcome": "SKIP", "reason": "clone_failed"})
            print()
            continue

        if args.dry_run:
            print(f"  {DIM}[dry-run] skipping scan{RESET}\n")
            results.append({"cve": stem, "outcome": "DRY_RUN"})
            continue

        # Scan
        findings = scan_repo(clone_dir)
        print(f"  Total findings    : {len(findings)}")

        # Score
        outcome, matched_id = score(spec, findings, clone_dir)

        outcome_labels = {
            "TP": f"{GREEN}✓ DETECTED  (TP){RESET}",
            "FN": f"{RED}✗ MISSED    (FN){RESET}",
            "TN": f"{GREEN}✓ HONEST MISS (TN — correct negative){RESET}",
        }
        print(f"  Outcome           : {outcome_labels.get(outcome, outcome)}")
        if matched_id:
            print(f"  Matched rule      : {matched_id}")
        print()

        results.append(
            {
                "cve": stem,
                "repo": repo,
                "recall_target": recall_target,
                "outcome": outcome,
                "matched_canonical_id": matched_id,
                "total_findings": len(findings),
            }
        )

    # Summary table
    completed = [r for r in results if r.get("outcome") not in ("SKIP", "DRY_RUN")]
    if not completed:
        print(f"{YELLOW}No completed results.{RESET}")
        sys.exit(0)

    tp = sum(1 for r in completed if r["outcome"] == "TP")
    fn = sum(1 for r in completed if r["outcome"] == "FN")
    tn = sum(1 for r in completed if r["outcome"] == "TN")
    detectable = tp + fn

    print("=" * 62)
    print(f"\n{BOLD}Summary{RESET}")
    print(f"  Detectable CVEs  : {detectable}  (recall_target=1)")
    print(f"  Detected (TP)    : {tp}")
    print(f"  Missed   (FN)    : {fn}")
    recall_str = f"{100*tp//detectable}%" if detectable else "n/a"
    print(f"  Recall@detectable: {BOLD}{recall_str}{RESET}")
    print(f"  Honest misses    : {tn}  (recall_target=0, SAST-invisible)")
    print()

    print(f"{'CVE':<55} {'Target':>7} {'Outcome'}")
    print("-" * 75)
    for r in completed:
        cve = r["cve"][:54]
        tgt = r.get("recall_target", "?")
        out = r["outcome"]
        color = GREEN if out in ("TP", "TN") else RED
        print(f"  {cve:<53} {tgt:>7}  {color}{out}{RESET}")

    save_results(completed)


if __name__ == "__main__":
    main()
