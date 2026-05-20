#!/usr/bin/env python3
"""ACR-QA Evaluation Runner — Phase A eval (v5.0.0b1).

Scans all curated repos against ground truth YAMLs, computes recall,
optionally runs Semgrep CE for head-to-head comparison, writes results.

Usage:
    python scripts/run_eval.py                 # scan + recall
    python scripts/run_eval.py --semgrep       # + Semgrep head-to-head
    python scripts/run_eval.py --dry-run       # print commands only
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")  # ensure DB_PORT=5434 etc. are set before any DB call
GT_DIR = ROOT / "TESTS" / "evaluation" / "ground_truth"
OUT_DIR = ROOT / "TESTS" / "evaluation" / "results"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# CVE repos are honestly "expected_findings: 0" — skip for recall; include in
# honest-limitations section of the paper.
CVE_PREFIXES = ("cve-",)


def _is_cve(yaml_name: str) -> bool:
    return any(yaml_name.startswith(p) for p in CVE_PREFIXES)


def load_ground_truth() -> list[dict]:
    entries = []
    for p in sorted(GT_DIR.glob("*.yml")):
        with open(p) as f:
            data = yaml.safe_load(f)
        data["_yaml_file"] = p.name
        entries.append(data)
    return entries


def scan_acrqa(
    target_dir: str,
    yaml_name: str,
    dry_run: bool = False,
    timeout: int = 900,
) -> list[dict]:
    out_file = OUT_DIR / f"acrqa-{yaml_name}.json"
    cmd = [
        sys.executable,
        str(ROOT / "CORE" / "main.py"),
        "--target-dir",
        target_dir,
        "--repo-name",
        yaml_name,
        "--no-ai",
        "--json",
    ]
    if dry_run:
        print(f"  [dry-run] {' '.join(cmd)}")
        return []
    print(f"  Scanning {target_dir} ...", end=" ", flush=True)
    t0 = time.time()
    outputs_dir = ROOT / "DATA" / "outputs"
    try:
        env = {**os.environ}  # already has dotenv loaded
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(ROOT), env=env)
        elapsed = time.time() - t0
        print(f"{elapsed:.0f}s")
        # 1. Try stdout JSON (--json flag) — most reliable, no stale-data risk
        findings = []
        stdout = proc.stdout.strip()
        if stdout.startswith("[") or stdout.startswith("{"):
            try:
                raw = json.loads(stdout)
                findings = raw if isinstance(raw, list) else raw.get("findings", [])
            except json.JSONDecodeError:
                pass
        # 2. Fall back: per-PID file written by this exact process (match proc.pid unavailable
        #    after Popen completes, so match by mtime strictly after t0 AND within the elapsed
        #    window — this prevents picking up files from concurrent test runs).
        if not findings and outputs_dir.exists():
            candidates = [
                p for p in outputs_dir.glob("findings_pid*.json") if t0 <= p.stat().st_mtime <= t0 + elapsed + 5
            ]
            if candidates:
                newest = max(candidates, key=lambda p: p.stat().st_mtime)
                try:
                    data = json.loads(newest.read_text())
                    # Reject synthetic test fixtures that leak from pytest runs
                    real = [f for f in data if f.get("message") != "Test security finding"]
                    if real:
                        findings = real
                except Exception:
                    pass
        # 3. Last resort: shared findings.json written strictly during this scan
        if not findings:
            fallback = outputs_dir / "findings.json"
            if fallback.exists() and t0 <= fallback.stat().st_mtime <= t0 + elapsed + 5:
                try:
                    data = json.loads(fallback.read_text())
                    findings = [f for f in data if f.get("message") != "Test security finding"]
                except Exception:
                    pass
        out_file.write_text(json.dumps(findings, indent=2))
        return findings
    except subprocess.TimeoutExpired:
        print(f"TIMEOUT (>{timeout}s)")
        out_file.write_text("[]")
        return []
    except Exception as exc:
        print(f"ERROR: {exc}")
        return []


def scan_semgrep(target_dir: str, yaml_name: str, dry_run: bool = False) -> list[dict]:
    out_file = OUT_DIR / f"semgrep-{yaml_name}.json"
    cmd = [
        "semgrep",
        "scan",
        "--config=auto",
        "--json",
        "--no-git-ignore",
        "--quiet",
        target_dir,
    ]
    if dry_run:
        print(f"  [dry-run] {' '.join(cmd)}")
        return []
    print(f"  Semgrep {target_dir} ...", end=" ", flush=True)
    t0 = time.time()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        elapsed = time.time() - t0
        print(f"{elapsed:.0f}s")
        data = json.loads(proc.stdout) if proc.stdout.strip() else {}
        findings = data.get("results", [])
        out_file.write_text(json.dumps(findings, indent=2))
        return findings
    except subprocess.TimeoutExpired:
        print("TIMEOUT")
        return []
    except Exception as exc:
        print(f"ERROR: {exc}")
        return []


def compute_recall(expected: list[dict], findings: list[dict], tool: str = "acrqa") -> dict:
    """Match expected findings against scan output.

    ACR-QA: match by canonical_rule_id (exact) or severity+file (soft).
    Semgrep: match by severity/check_id keyword or HIGH-severity presence per file.
    """
    if not expected:
        return {"expected": 0, "found": 0, "recall": None, "matched": []}
    if not findings:
        return {"expected": len(expected), "found": 0, "matched": 0, "recall": 0.0, "match_detail": []}

    if tool == "acrqa":
        found_rules = {(f.get("canonical_rule_id") or f.get("rule_id") or "").upper() for f in findings}
        found_sev_files = {
            (
                (f.get("canonical_severity") or f.get("severity") or "").lower(),
                Path(f.get("file_path") or f.get("file") or "").name,
            )
            for f in findings
        }
        matched = []
        for exp in expected:
            cid = (exp.get("canonical_id") or "").upper()
            sev = (exp.get("severity") or "high").lower()
            exp_file = Path(exp.get("file_path") or exp.get("file") or "").name
            if cid and cid in found_rules:
                matched.append({"id": exp.get("id"), "match": "exact_rule"})
            elif (sev, exp_file) in found_sev_files:
                matched.append({"id": exp.get("id"), "match": "severity+file"})
            elif sev in {s for s, _ in found_sev_files}:
                matched.append({"id": exp.get("id"), "match": "severity_only"})
    else:
        # Semgrep: findings have check_id, path, extra.severity
        sg_high_files = {
            Path(f.get("path") or "").name
            for f in findings
            if (f.get("extra", {}).get("severity") or "").lower() in ("error", "warning", "high")
        }
        sg_any_files = {Path(f.get("path") or "").name for f in findings}
        matched = []
        for exp in expected:
            exp_file = Path(exp.get("file_path") or exp.get("file") or "").name
            if exp_file and exp_file in sg_high_files:
                matched.append({"id": exp.get("id"), "match": "file+severity"})
            elif exp_file and exp_file in sg_any_files:
                matched.append({"id": exp.get("id"), "match": "file_any"})

    recall = len(matched) / len(expected)
    return {
        "expected": len(expected),
        "found": len(findings),
        "matched": len(matched),
        "recall": round(recall, 3),
        "match_detail": matched,
    }


def resolve_local_path(entry: dict) -> str | None:
    lp = entry.get("local_path", "")
    candidates = [
        Path(lp),
        ROOT / lp,
        ROOT / "test_targets" / "eval-repos" / entry.get("repo", "").split("@")[0].lower(),
    ]
    for c in candidates:
        if c.is_dir():
            # scan_subdir lets a YAML focus the scan on a subdirectory (e.g.
            # bandit-test-cases scans examples/ only, not the full bandit source tree).
            subdir = entry.get("scan_subdir", "")
            if subdir:
                target = c / subdir
                if target.is_dir():
                    return str(target)
            return str(c)
    return None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="ACR-QA Eval Runner")
    p.add_argument("--semgrep", action="store_true", help="Also run Semgrep CE for head-to-head")
    p.add_argument("--dry-run", action="store_true", help="Print commands, don't execute")
    p.add_argument("--cve", action="store_true", help="Also scan CVE repos (default: skip)")
    p.add_argument("--cve-only", action="store_true", help="Scan CVE repos only (skip non-CVE benchmark repos)")
    p.add_argument(
        "--timeout",
        type=int,
        default=900,
        help="Per-repo ACR-QA scan timeout in seconds (default: 900)",
    )
    args = p.parse_args(argv)
    if args.cve_only:
        args.cve = True  # cve-only implies --cve

    entries = load_ground_truth()
    print(f"Loaded {len(entries)} ground-truth YAMLs")

    results = []
    for entry in entries:
        name = entry["_yaml_file"]
        if args.cve_only and not _is_cve(name):
            continue  # skip non-CVE repos when --cve-only
        if _is_cve(name) and not args.cve:
            print(f"[skip CVE] {name}")
            results.append(
                {
                    "yaml": name,
                    "repo": entry.get("repo"),
                    "skipped": "cve",
                    "note": "Protocol-level CVE — static analysis limitation (honest)",
                }
            )
            continue

        local_path = resolve_local_path(entry)
        if not local_path:
            print(f"[missing] {name} — no local path, skipping")
            results.append({"yaml": name, "repo": entry.get("repo"), "skipped": "no_local_path"})
            continue

        print(f"\n[{name}]")
        expected = entry.get("expected_findings", [])

        acrqa_findings = scan_acrqa(local_path, name, dry_run=args.dry_run, timeout=args.timeout)
        acrqa_recall = compute_recall(expected, acrqa_findings)

        row = {
            "yaml": name,
            "repo": entry.get("repo"),
            "language": entry.get("language"),
            "expected_count": len(expected),
            "acrqa": acrqa_recall,
        }

        if args.semgrep:
            sg_findings = scan_semgrep(local_path, name, dry_run=args.dry_run)
            sg_recall = compute_recall(expected, sg_findings)
            row["semgrep"] = sg_recall

        results.append(row)

    if args.dry_run:
        return 0

    # ── Summary table ─────────────────────────────────────────────────────────
    scanned = [r for r in results if "acrqa" in r]
    cve_skipped = [r for r in results if r.get("skipped") == "cve"]
    missing = [r for r in results if r.get("skipped") == "no_local_path"]

    recalls = [r["acrqa"]["recall"] for r in scanned if r["acrqa"].get("recall") is not None]
    avg_recall = sum(recalls) / len(recalls) if recalls else 0.0

    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    print(f"Repos scanned:        {len(scanned)}")
    print(f"CVE repos skipped:    {len(cve_skipped)} (honest limitations)")
    print(f"Missing local path:   {len(missing)}")
    print(f"Average recall:       {avg_recall:.1%}")
    print()
    print(f"{'Repo':<35} {'Exp':>4} {'Found':>6} {'Recall':>8}", end="")
    if args.semgrep:
        print(f" {'Semgrep':>8}", end="")
    print()
    print("-" * (60 if not args.semgrep else 72))
    for r in scanned:
        ac = r["acrqa"]
        recall_str = f"{ac['recall']:.0%}" if ac.get("recall") is not None else "N/A"
        print(f"{r['repo']:<35} {ac['expected']:>4} {ac['found']:>6} {recall_str:>8}", end="")
        if args.semgrep and "semgrep" in r:
            sg = r["semgrep"]
            sg_str = f"{sg['recall']:.0%}" if sg.get("recall") is not None else "N/A"
            print(f" {sg_str:>8}", end="")
        print()

    # ── Write JSON results ────────────────────────────────────────────────────
    summary = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_repos": len(entries),
        "scanned": len(scanned),
        "cve_skipped": len(cve_skipped),
        "average_recall": round(avg_recall, 3),
        "results": results,
    }
    out_json = OUT_DIR / "eval_summary.json"
    out_json.write_text(json.dumps(summary, indent=2))
    print(f"\nResults written to {out_json}")

    # ── Update BENCHMARK_v5.md ────────────────────────────────────────────────
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_benchmarks.py"), "--write-md"],
        cwd=str(ROOT),
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
