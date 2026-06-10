#!/usr/bin/env python3
"""T19 Robustness / FP-harvest evaluation harness.

Scans every repo in TESTS/evaluation/robustness/PREREGISTERED_REPOS.yml
using the pre-registered split discipline (DEV scanned freely;
HELD scanned ONCE after DEV tuning is done).

Usage:
    # Scan DEV set (tune freely):
    python scripts/run_robustness_eval.py --set dev

    # Scan HELD set (run ONCE, never tune after):
    python scripts/run_robustness_eval.py --set held

    # Scan a single repo by name:
    python scripts/run_robustness_eval.py --repo pyjwt

    # Clone only (no scan):
    python scripts/run_robustness_eval.py --set dev --clone-only

    # Skip cloning (repos already present):
    python scripts/run_robustness_eval.py --set dev --no-clone

    # Write results to markdown:
    python scripts/run_robustness_eval.py --set dev --write-md

Output:
    TESTS/evaluation/robustness/results/<name>_result.json  — per-repo JSON
    TESTS/evaluation/robustness/results/summary.json        — all-repo summary
    docs/evaluation/ROBUSTNESS_T19.md                       — thesis report (--write-md)
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML required: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = REPO_ROOT / "TESTS" / "evaluation" / "robustness" / "PREREGISTERED_REPOS.yml"
RESULTS_DIR = REPO_ROOT / "TESTS" / "evaluation" / "robustness" / "results"
CLONE_BASE = REPO_ROOT / "TESTS" / "evaluation" / "robustness" / "cloned"
REPORT_PATH = REPO_ROOT / "docs" / "evaluation" / "ROBUSTNESS_T19.md"
MAIN_PY = REPO_ROOT / "CORE" / "main.py"

SEV_ORDER = {"high": 0, "medium": 1, "low": 2}


# ---------------------------------------------------------------------------
# Manifest loading
# ---------------------------------------------------------------------------


def load_manifest() -> dict:
    with MANIFEST.open() as f:
        return yaml.safe_load(f)


def select_repos(manifest: dict, set_name: str, single: str | None) -> list[dict]:
    """Return repos matching set_name ('dev' | 'held' | 'all') or single name."""
    dev = manifest.get("dev", [])
    held = manifest.get("held", [])

    if single:
        for r in dev + held:
            if r["name"] == single:
                return [r]
        print(f"[error] repo '{single}' not found in manifest", file=sys.stderr)
        sys.exit(1)

    if set_name == "dev":
        return dev
    if set_name == "held":
        return held
    return dev + held


# ---------------------------------------------------------------------------
# Cloning
# ---------------------------------------------------------------------------


def clone_repo(repo: dict, clone_base: Path, force: bool = False) -> Path:
    name = repo["name"]
    github = repo["github"]
    ref = repo["ref"]
    target = clone_base / name

    if target.exists() and not force:
        print(f"  [skip clone] {name} already at {target}")
        return target

    if target.exists():
        shutil.rmtree(target)

    url = f"https://github.com/{github}.git"
    print(f"  [clone] {name} @ {ref} …", end=" ", flush=True)
    t0 = time.monotonic()
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", ref, url, str(target)],
            check=True,
            capture_output=True,
            timeout=120,
        )
        elapsed = time.monotonic() - t0
        print(f"done ({elapsed:.1f}s)")
    except subprocess.CalledProcessError as e:
        print(f"FAILED\n  stderr: {e.stderr.decode()[:200]}")
        raise
    except subprocess.TimeoutExpired:
        print("TIMEOUT")
        raise

    return target


# ---------------------------------------------------------------------------
# Scanning
# ---------------------------------------------------------------------------


def scan_repo(repo: dict, clone_dir: Path) -> dict:
    """Run ACR-QA --no-ai against the cloned repo and return a result dict."""
    name = repo["name"]
    print(f"  [scan] {name} …", end=" ", flush=True)
    t0 = time.monotonic()

    cmd = [
        sys.executable, str(MAIN_PY),
        "--target-dir", str(clone_dir),
        "--no-ai",
        "--lang", "python",
        "--json",
    ]

    result = {
        "name": name,
        "github": repo["github"],
        "ref": repo["ref"],
        "set": "dev" if repo.get("contaminated") or name in _dev_names else "held",
        "scanned_at": datetime.now(tz=timezone.utc).isoformat(),
        "scan_time_s": 0.0,
        "crashed": False,
        "crash_message": None,
        "total_findings": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
        "findings_sample": [],
        "raw_json_path": None,
    }

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            timeout=600,  # 10 min max (larger repos can take 5-8 min)
            cwd=str(REPO_ROOT),
        )
        elapsed = time.monotonic() - t0
        result["scan_time_s"] = round(elapsed, 2)

        stdout = proc.stdout.decode("utf-8", errors="replace")
        stderr = proc.stderr.decode("utf-8", errors="replace")

        # ACR-QA --json writes findings to stdout
        findings: list[dict] = []
        if stdout.strip():
            try:
                findings = json.loads(stdout)
                if not isinstance(findings, list):
                    findings = []
            except json.JSONDecodeError:
                # Might have mixed logging + JSON; try to extract JSON array
                for line in stdout.split("\n"):
                    stripped = line.strip()
                    if stripped.startswith("["):
                        try:
                            findings = json.loads(stripped)
                            break
                        except json.JSONDecodeError:
                            pass

        result["total_findings"] = len(findings)
        result["high"] = sum(1 for f in findings if f.get("canonical_severity") == "high")
        result["medium"] = sum(1 for f in findings if f.get("canonical_severity") == "medium")
        result["low"] = sum(1 for f in findings if f.get("canonical_severity") == "low")

        # Save top-5 HIGH findings as sample
        high_f = [f for f in findings if f.get("canonical_severity") == "high"]
        result["findings_sample"] = [
            {
                "rule": f.get("canonical_rule_id"),
                "file": f.get("file", f.get("file_path", "")),
                "line": f.get("line", f.get("line_number", 0)),
                "message": (f.get("message", "") or "")[:120],
                "in_test_file": _is_test_path(f.get("file", f.get("file_path", ""))),
            }
            for f in high_f[:5]
        ]

        if proc.returncode not in (0, 1):  # 1 = gate failed (normal)
            result["crashed"] = True
            result["crash_message"] = (stderr[-500:] if stderr else "exit code " + str(proc.returncode))

        print(f"done ({elapsed:.1f}s) | H={result['high']} M={result['medium']} L={result['low']}")

    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - t0
        result["scan_time_s"] = round(elapsed, 2)
        result["crashed"] = True
        result["crash_message"] = "scan timeout (>600s)"
        print(f"TIMEOUT ({elapsed:.1f}s)")

    except Exception as exc:
        elapsed = time.monotonic() - t0
        result["scan_time_s"] = round(elapsed, 2)
        result["crashed"] = True
        result["crash_message"] = str(exc)[:300]
        print(f"ERROR: {exc}")

    return result


def _is_test_path(path: str) -> bool:
    import re

    _TEST_RE = re.compile(
        r"(?:^|/)(tests?|testing|test_|_test\.|spec[_/]|fixtures?|examples?|benchmarks?|demos?)",
        re.IGNORECASE,
    )
    return bool(_TEST_RE.search(path or ""))


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def write_markdown_report(results: list[dict], manifest: dict) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    scan_date = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")

    total = len(results)
    crashed = sum(1 for r in results if r["crashed"])
    total_findings = sum(r["total_findings"] for r in results)
    total_high = sum(r["high"] for r in results)
    high_in_test = sum(
        sum(1 for f in r["findings_sample"] if f.get("in_test_file"))
        for r in results
    )

    dev_results = [r for r in results if r["set"] == "dev"]
    held_results = [r for r in results if r["set"] == "held"]

    lines = [
        "# T19 — Robustness / FP-harvest Study",
        "",
        f"**Scan date:** {scan_date}  ",
        f"**Scanner version:** {manifest['meta']['scanner_version']}  ",
        f"**Flags:** `{manifest['meta']['scan_flags']}`  ",
        f"**Corpus:** {total} repos ({len(dev_results)} DEV · {len(held_results)} HELD)  ",
        f"**Pre-registration commit:** see `TESTS/evaluation/robustness/PREREGISTERED_REPOS.yml`",
        "",
        "---",
        "",
        "## Summary",
        "",
        f"| Metric | DEV ({len(dev_results)}) | HELD ({len(held_results)}) | ALL ({total}) |",
        "|---|---|---|---|",
    ]

    def _stat(rs: list[dict], key: str) -> str:
        return str(sum(r[key] for r in rs)) if rs else "—"

    lines += [
        f"| Repos scanned | {len(dev_results)} | {len(held_results)} | {total} |",
        f"| Crashes / timeouts | {_stat(dev_results, 'crashed')} | {_stat(held_results, 'crashed')} | {crashed} |",
        f"| Total findings | {_stat(dev_results, 'total_findings')} | {_stat(held_results, 'total_findings')} | {total_findings} |",
        f"| HIGH findings | {_stat(dev_results, 'high')} | {_stat(held_results, 'high')} | {total_high} |",
        f"| Avg scan time (s) | {_avg_time(dev_results)} | {_avg_time(held_results)} | {_avg_time(results)} |",
        "",
        "---",
        "",
        "## Per-repo results",
        "",
        "| Repo | Set | Scan (s) | HIGH | MED | LOW | Crash? |",
        "|---|---|---|---|---|---|---|",
    ]

    for r in sorted(results, key=lambda x: (x["set"], x["name"])):
        crash_str = "❌ " + (r["crash_message"] or "")[:40] if r["crashed"] else "✅"
        lines.append(
            f"| {r['name']} @{r['ref']} | {r['set'].upper()} | {r['scan_time_s']} "
            f"| {r['high']} | {r['medium']} | {r['low']} | {crash_str} |"
        )

    lines += [
        "",
        "---",
        "",
        "## HIGH findings sample (top 5 per repo where HIGH > 0)",
        "",
    ]

    for r in results:
        if r["high"] > 0 and r["findings_sample"]:
            lines.append(f"### {r['name']} ({r['set'].upper()})")
            lines.append("")
            lines.append("| Rule | File | Line | In-test? | Message |")
            lines.append("|---|---|---|---|---|")
            for f in r["findings_sample"]:
                test_flag = "⚠️ test" if f.get("in_test_file") else "source"
                lines.append(
                    f"| `{f['rule']}` | `{f['file']}` | {f['line']} | {test_flag} | {f['message'][:60]} |"
                )
            lines.append("")

    lines += [
        "---",
        "",
        "## Key findings & fixes",
        "",
        "_(populated after DEV scan pass — list real bugs found and their fixes)_",
        "",
        "| # | Repo | Finding | Type | Fix |",
        "|---|---|---|---|---|",
        "",
        "---",
        "",
        "## Methodology note",
        "",
        "The pre-registered list was committed to",
        "`TESTS/evaluation/robustness/PREREGISTERED_REPOS.yml` **before** any scanning.",
        "The DEV set was inspected and tuned freely; the HELD set was scanned **once**",
        "after DEV tuning was complete. No tuning was performed based on HELD results.",
        "This follows the anti-overfitting discipline described in §7b of the project plan.",
        "",
    ]

    REPORT_PATH.write_text("\n".join(lines))
    print(f"\n[report] Written to {REPORT_PATH}")


def _avg_time(results: list[dict]) -> str:
    if not results:
        return "—"
    times = [r["scan_time_s"] for r in results if not r["crashed"]]
    if not times:
        return "n/a"
    return f"{sum(times) / len(times):.1f}"


# ---------------------------------------------------------------------------
# Global state (populated by main)
# ---------------------------------------------------------------------------
_dev_names: set[str] = set()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="T19 Robustness evaluation harness")
    parser.add_argument("--set", choices=["dev", "held", "all"], default="dev",
                        help="Which set to process (default: dev)")
    parser.add_argument("--repo", metavar="NAME",
                        help="Scan a single repo by name")
    parser.add_argument("--clone-only", action="store_true",
                        help="Clone repos but do not scan")
    parser.add_argument("--no-clone", action="store_true",
                        help="Skip cloning (repos already present)")
    parser.add_argument("--force-clone", action="store_true",
                        help="Re-clone even if repo already exists")
    parser.add_argument("--write-md", action="store_true",
                        help="Write markdown report to docs/evaluation/ROBUSTNESS_T19.md")
    parser.add_argument("--output", metavar="PATH",
                        help="Write JSON summary to PATH")
    args = parser.parse_args()

    manifest = load_manifest()
    global _dev_names
    _dev_names = {r["name"] for r in manifest.get("dev", [])}

    repos = select_repos(manifest, args.set, args.repo)
    CLONE_BASE.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"T19 Robustness Eval — {len(repos)} repo(s) [{args.set.upper()}]")
    print(f"{'='*60}\n")

    results: list[dict] = []

    for repo in repos:
        name = repo["name"]
        contaminated = repo.get("contaminated", False)
        print(f"\n[{name}] {'(⚠️  contaminated — DEV)' if contaminated else ''}")

        # Clone
        clone_dir = CLONE_BASE / name
        if not args.no_clone:
            try:
                clone_dir = clone_repo(repo, CLONE_BASE, force=args.force_clone)
            except Exception as exc:
                print(f"  [skip] clone failed: {exc}")
                results.append({
                    "name": name, "github": repo["github"], "ref": repo["ref"],
                    "set": "dev" if name in _dev_names else "held",
                    "scanned_at": datetime.now(tz=timezone.utc).isoformat(),
                    "scan_time_s": 0.0, "crashed": True,
                    "crash_message": f"clone failed: {exc}",
                    "total_findings": 0, "high": 0, "medium": 0, "low": 0,
                    "findings_sample": [], "raw_json_path": None,
                })
                continue

        if args.clone_only:
            continue

        if not clone_dir.exists():
            print(f"  [skip] {clone_dir} does not exist — run without --no-clone first")
            continue

        # Scan
        result = scan_repo(repo, clone_dir)
        result["set"] = "dev" if name in _dev_names else "held"

        # Persist per-repo JSON
        result_path = RESULTS_DIR / f"{name}_result.json"
        result_path.write_text(json.dumps(result, indent=2))
        result["raw_json_path"] = str(result_path)
        results.append(result)

    if args.clone_only:
        print("\n[done] Clone-only mode; no scans run.")
        return

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for r in results:
        status = "CRASH" if r["crashed"] else "OK"
        print(
            f"  {r['name']:20s} [{r['set'].upper():4s}] {status:5s} "
            f"H={r['high']:3d} M={r['medium']:3d} L={r['low']:3d} "
            f"({r['scan_time_s']:.1f}s)"
        )

    # Write summary JSON
    summary_path = RESULTS_DIR / "summary.json"
    summary_path.write_text(json.dumps({
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "scanner_version": manifest["meta"]["scanner_version"],
        "repos": results,
    }, indent=2))
    print(f"\n[saved] {summary_path}")

    if args.output:
        Path(args.output).write_text(json.dumps(results, indent=2))
        print(f"[saved] {args.output}")

    if args.write_md:
        write_markdown_report(results, manifest)


if __name__ == "__main__":
    main()
