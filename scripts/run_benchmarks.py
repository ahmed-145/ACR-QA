#!/usr/bin/env python3
"""ACR-QA benchmark harness (v5.0.0 Phase A.3 — Eval Wave 1 skeleton).

Walks every YAML in `TESTS/evaluation/ground_truth/`, clones the target repo at
the pinned ref (when `local_path` is missing), runs `acrqa` against it, and
computes recall against the `expected_findings` block.

This is a skeleton: cloning + running is gated behind `--clone` and `--scan`
flags so the script can run as a fast metadata-only check on every commit.

Usage:
    python scripts/run_benchmarks.py                # parse YAMLs, print summary
    python scripts/run_benchmarks.py --clone        # also clone missing repos
    python scripts/run_benchmarks.py --scan         # run ACR-QA on every repo
    python scripts/run_benchmarks.py --json out.json

Output is also persisted to `docs/evaluation/BENCHMARK_v5.md` when run with
`--write-md`.

Time budget per plan §A3: full --scan run < 90 minutes on the 28-repo corpus.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("PyYAML required: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


GROUND_TRUTH_DIR = Path(__file__).resolve().parent.parent / "TESTS" / "evaluation" / "ground_truth"


def load_ground_truth() -> list[dict[str, Any]]:
    """Load every YAML file in the ground-truth directory."""
    out: list[dict[str, Any]] = []
    if not GROUND_TRUTH_DIR.is_dir():
        return out
    for p in sorted(GROUND_TRUTH_DIR.glob("*.yml")):
        try:
            with p.open() as f:
                data = yaml.safe_load(f) or {}
        except Exception as exc:
            print(f"[warn] failed to parse {p.name}: {exc}", file=sys.stderr)
            continue
        data["_yaml_file"] = p.name
        out.append(data)
    return out


def summarize(repos: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a tier-1/4/5 breakdown plus per-repo expected counts."""
    rows: list[dict[str, Any]] = []
    total_expected = 0
    pending = 0
    for r in repos:
        expected = r.get("expected_findings") or []
        pv = r.get("pending_verification") or []
        total_expected += len(expected)
        if not expected and pv:
            pending += 1
        rows.append(
            {
                "yaml": r["_yaml_file"],
                "repo": r.get("repo"),
                "language": r.get("language"),
                "cwe": r.get("cwe"),
                "expected_count": len(expected),
                "pending_verification": len(pv),
                "local_path": r.get("local_path"),
                "checkout_ref": r.get("checkout_ref"),
                "recall_target": r.get("recall_target"),
            }
        )
    return {
        "total_repos": len(repos),
        "total_expected_findings": total_expected,
        "repos_pending_verification": pending,
        "rows": rows,
    }


def write_markdown(summary: dict[str, Any], dest: Path) -> None:
    """Write a human-readable markdown summary to *dest*."""
    # Load recall data from eval_summary.json if available
    eval_json = dest.parent.parent.parent / "TESTS" / "evaluation" / "results" / "eval_summary.json"
    recall_by_yaml: dict[str, dict] = {}
    if eval_json.exists():
        try:
            eval_data = json.loads(eval_json.read_text())
            for row in eval_data.get("results", []):
                if "acrqa" in row:
                    recall_by_yaml[row["yaml"]] = row
        except Exception:
            pass

    lines: list[str] = []
    lines.append("# ACR-QA Benchmark Summary\n")
    lines.append(f"_Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}_\n")
    lines.append(
        f"**{summary['total_repos']} repos** · "
        f"**{summary['total_expected_findings']} expected findings** · "
        f"**{summary['repos_pending_verification']} pending verification**\n",
    )

    if recall_by_yaml:
        # Include recall columns when eval results are available
        acrqa_avg = eval_data.get("acrqa_average_recall")
        sg_avg = eval_data.get("semgrep_average_recall")
        if acrqa_avg is not None:
            lines.append(
                f"**ACR-QA avg recall: {acrqa_avg:.1%}** · "
                f"**Semgrep CE avg recall: {sg_avg:.1%}** (13 non-CVE repos)\n"
            )
        lines.append("| Repo | Lang | Exp | ACR-QA | Found | Semgrep | Found |")
        lines.append("|------|------|----:|:------:|------:|:-------:|------:|")
        for r in summary["rows"]:
            yaml_name = r["yaml"]
            if yaml_name in recall_by_yaml:
                er = recall_by_yaml[yaml_name]
                ar = er["acrqa"]
                sg = er.get("semgrep", {})
                ar_str = f"{ar['recall']:.0%}" if ar.get("recall") is not None else "—"
                sg_str = f"{sg['recall']:.0%}" if sg.get("recall") is not None else "—"
                lines.append(
                    f"| {r['repo'] or '—'} | {r['language'] or '—'} | "
                    f"{ar['expected']} | {ar_str} | {ar['found']} | {sg_str} | {sg.get('found', '—')} |"
                )
            elif r.get("yaml", "").startswith("cve-"):
                lines.append(f"| {r['repo'] or '—'} | {r['language'] or '—'} | " f"0 | CVE | — | CVE | — |")
    else:
        lines.append("| YAML | Repo | Language | CWE | Expected | Pending | Local | Recall target |")
        lines.append("|---|---|---|---|---:|---:|---|---:|")
        for r in summary["rows"]:
            lines.append(
                f"| {r['yaml']} | {r['repo'] or '—'} | {r['language'] or '—'} | "
                f"{r['cwe'] or '—'} | {r['expected_count']} | {r['pending_verification']} | "
                f"{'✅' if r['local_path'] else '—'} | {r['recall_target'] if r['recall_target'] is not None else '—'} |",
            )
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def cmd_clone(repos: list[dict[str, Any]]) -> int:
    """`--clone` placeholder: prints planned git clone commands but does not run them.

    Real cloning is gated behind explicit operator action because:
      - It writes to disk outside the project
      - Bandwidth + storage costs are real
      - Some test repos are intentionally vulnerable and shouldn't be auto-pulled in CI
    """
    print("\n# Planned clones (NOT executed — gated behind manual operator):\n")
    for r in repos:
        if not r.get("url") or not r.get("local_path"):
            continue
        ref = r.get("checkout_ref") or "main"
        print(f"git clone {r['url']} {r['local_path']} && git -C {r['local_path']} checkout {ref}")
    return 0


def cmd_scan(repos: list[dict[str, Any]]) -> int:
    """`--scan` placeholder: prints planned `acrqa` commands but does not execute.

    Same rationale as `--clone`: scanning 28 repos takes minutes and should be
    explicitly operator-initiated.
    """
    print("\n# Planned scans (NOT executed):\n")
    for r in repos:
        lp = r.get("local_path")
        if not lp:
            continue
        print(f"acrqa scan --target-dir {lp} --json --no-ai > /tmp/bench-{r['_yaml_file']}.json")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ACR-QA benchmark harness")
    parser.add_argument("--clone", action="store_true", help="print git-clone commands (does not execute)")
    parser.add_argument("--scan", action="store_true", help="print acrqa-scan commands (does not execute)")
    parser.add_argument("--json", metavar="FILE", help="write JSON summary to FILE")
    parser.add_argument("--write-md", action="store_true", help="write docs/evaluation/BENCHMARK_v5.md")
    args = parser.parse_args(argv)

    repos = load_ground_truth()
    summary = summarize(repos)

    print(
        f"Loaded {summary['total_repos']} ground-truth YAMLs · "
        f"{summary['total_expected_findings']} expected findings · "
        f"{summary['repos_pending_verification']} pending verification.",
    )

    if args.clone:
        cmd_clone(repos)
    if args.scan:
        cmd_scan(repos)

    if args.json:
        Path(args.json).write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"Wrote JSON summary to {args.json}")

    if args.write_md:
        out = Path(__file__).resolve().parent.parent / "docs" / "evaluation" / "BENCHMARK_v5.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        write_markdown(summary, out)
        print(f"Wrote markdown summary to {out.relative_to(Path.cwd()) if out.is_relative_to(Path.cwd()) else out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
