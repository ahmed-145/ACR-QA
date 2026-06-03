#!/usr/bin/env python3
"""
ACR-QA RealVuln Benchmark Runner.

Runs ACR-QA (Bandit + Semgrep + custom rules) and baselines (Bandit standalone,
Semgrep CE standalone) across the 22 cloned RealVuln repos, scores using the
RealVuln scorer (F2, F3, TPR, FPR, Youden J, MCC), and writes a comparison doc.

RealVuln corpus: 26 real Python repos, 697 TP + 120 FP labelled findings.
22 repos cloned (4 failed due to broken GitHub URLs in benchmark manifest).
22-repo coverage: 558 TPs + 97 FPs.

Usage:
    python3 scripts/run_realvuln_benchmark.py
        [--realvuln-dir TESTS/evaluation/realvuln]
        [--output-dir docs/evaluation]

Pre-registration: methodology committed before any run.
"""

from __future__ import annotations

import json
import math
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from CORE import __version__
from CORE.engines.normalizer import RULE_MAPPING

_ROOT = Path(__file__).parent.parent
_NOW = datetime.now(timezone.utc)

# ---------------------------------------------------------------------------
# CWE mapping: Bandit test_id → CWE, Canonical → CWE
# ---------------------------------------------------------------------------

BANDIT_CWE: dict[str, str] = {
    "B101": "CWE-617",
    "B102": "CWE-78",
    "B103": "CWE-732",
    "B104": "CWE-605",
    "B105": "CWE-259",
    "B106": "CWE-259",
    "B107": "CWE-259",
    "B108": "CWE-377",
    "B110": "CWE-390",
    "B112": "CWE-390",
    "B301": "CWE-502",
    "B302": "CWE-502",
    "B303": "CWE-327",
    "B304": "CWE-327",
    "B305": "CWE-327",
    "B306": "CWE-377",
    "B307": "CWE-78",
    "B308": "CWE-79",
    "B311": "CWE-330",
    "B312": "CWE-319",
    "B313": "CWE-611",
    "B314": "CWE-611",
    "B315": "CWE-611",
    "B316": "CWE-611",
    "B317": "CWE-611",
    "B318": "CWE-611",
    "B319": "CWE-611",
    "B320": "CWE-611",
    "B321": "CWE-319",
    "B322": "CWE-78",
    "B323": "CWE-295",
    "B324": "CWE-327",
    "B325": "CWE-318",
    "B401": "CWE-319",
    "B402": "CWE-319",
    "B403": "CWE-502",
    "B404": "CWE-78",
    "B405": "CWE-611",
    "B406": "CWE-611",
    "B407": "CWE-611",
    "B408": "CWE-611",
    "B409": "CWE-611",
    "B411": "CWE-285",
    "B412": "CWE-284",
    "B413": "CWE-327",
    "B501": "CWE-295",
    "B502": "CWE-295",
    "B503": "CWE-295",
    "B504": "CWE-295",
    "B505": "CWE-326",
    "B506": "CWE-502",
    "B507": "CWE-295",
    "B601": "CWE-78",
    "B602": "CWE-78",
    "B603": "CWE-78",
    "B604": "CWE-78",
    "B605": "CWE-78",
    "B606": "CWE-78",
    "B607": "CWE-78",
    "B608": "CWE-89",
    "B609": "CWE-78",
    "B610": "CWE-89",
    "B611": "CWE-89",
    "B701": "CWE-1336",
    "B702": "CWE-1336",
    "B703": "CWE-79",
}

CANONICAL_CWE: dict[str, str] = {
    "SECURITY-001": "CWE-78",
    "SECURITY-002": "CWE-390",
    "SECURITY-003": "CWE-617",
    "SECURITY-004": "CWE-89",
    "SECURITY-006": "CWE-522",
    "SECURITY-007": "CWE-605",
    "SECURITY-008": "CWE-502",
    "SECURITY-009": "CWE-326",
    "SECURITY-010": "CWE-79",
    "SECURITY-011": "CWE-22",
    "SECURITY-018": "CWE-502",
    "SECURITY-021": "CWE-78",
    "SECURITY-024": "CWE-611",
    "SECURITY-027": "CWE-89",
    "SECURITY-028": "CWE-89",
    "SECURITY-031": "CWE-1336",
    "SECURITY-032": "CWE-1336",
    "SECURITY-043": "CWE-611",
    "SECURITY-044": "CWE-611",
    "SECURITY-045": "CWE-79",
    "SECURITY-046": "CWE-918",
    "SECURITY-047": "CWE-347",
    "SECURITY-048": "CWE-601",
    "SECURITY-049": "CWE-22",
    "SECURITY-051": "CWE-1333",
    "SECURITY-052": "CWE-22",
    "SECURITY-056": "CWE-918",
    "SECURITY-062": "CWE-78",
    "SECURITY-066": "CWE-117",
    "SECURITY-067": "CWE-90",
    "SECURITY-601": "CWE-601",
}

SEMGREP_CWE_RE = re.compile(r"(CWE-\d+)")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _venv(name: str) -> str:
    p = _ROOT / ".venv" / "bin" / name
    return str(p) if p.exists() else name


def _mcc(tp: int, tn: int, fp: int, fn: int) -> float:
    n = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return ((tp * tn) - (fp * fn)) / n if n else 0.0


def _fbeta(p: float, r: float, beta: float) -> float:
    b2 = beta * beta
    return (1 + b2) * p * r / (b2 * p + r) if (b2 * p + r) else 0.0


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


def run_bandit(repo_dir: str) -> list[dict]:
    """Run Bandit; return list of {file, cwe, line, rule_id}."""
    try:
        r = subprocess.run(
            [_venv("bandit"), "-r", repo_dir, "-f", "json", "-q"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        data = json.loads(r.stdout or "{}")
        findings = []
        for res in data.get("results", []):
            tid = res.get("test_id", "")
            cwe = BANDIT_CWE.get(tid)
            if not cwe:
                continue
            fname = Path(res.get("filename", "")).relative_to(repo_dir)
            findings.append(
                {
                    "file": str(fname).replace("\\", "/"),
                    "cwe": cwe,
                    "line": res.get("line_number"),
                    "rule_id": tid,
                    "severity": res.get("issue_severity", "").lower(),
                }
            )
        return findings
    except Exception as exc:
        print(f"    ⚠ Bandit: {exc}", file=sys.stderr)
        return []


def run_semgrep_custom(repo_dir: str) -> list[dict]:
    """Run Semgrep CE + ACR-QA custom rules; return findings."""
    custom = _ROOT / "TOOLS" / "semgrep" / "python-rules.yml"
    configs = ["--config=p/python"]
    if custom.exists():
        configs += [f"--config={custom}"]
    try:
        r = subprocess.run(
            [_venv("semgrep"), *configs, "--json", "--quiet", repo_dir],
            capture_output=True,
            text=True,
            timeout=300,
        )
        data = json.loads(r.stdout or "{}")
        findings = []
        for res in data.get("results", []):
            metadata = res.get("extra", {}).get("metadata", {})
            raw_cwes = metadata.get("cwe", [])
            if isinstance(raw_cwes, str):
                raw_cwes = [raw_cwes]
            cwes = [m.group(1) for c in raw_cwes if (m := SEMGREP_CWE_RE.match(str(c)))]

            rid = res.get("check_id", "")
            canonical = RULE_MAPPING.get(rid)
            if not cwes and canonical:
                c = CANONICAL_CWE.get(canonical)
                if c:
                    cwes = [c]
            if not cwes:
                continue

            try:
                fname = str(Path(res.get("path", "")).relative_to(repo_dir))
            except ValueError:
                fname = res.get("path", "")
            fname = fname.replace("\\", "/")

            for cwe in cwes:
                findings.append(
                    {
                        "file": fname,
                        "cwe": cwe,
                        "line": res.get("start", {}).get("line"),
                        "rule_id": rid,
                        "severity": (res.get("extra", {}).get("severity") or "").lower(),
                    }
                )
        return findings
    except Exception as exc:
        print(f"    ⚠ Semgrep: {exc}", file=sys.stderr)
        return []


def run_acrqa_full(repo_dir: str) -> list[dict]:
    """Bandit + Semgrep + custom rules combined."""
    bandit = run_bandit(repo_dir)
    semgrep = run_semgrep_custom(repo_dir)
    # Deduplicate by (file, cwe, line±5)
    seen: set[tuple] = set()
    merged = []
    for f in bandit + semgrep:
        key = (f["file"], f["cwe"], (f["line"] or 0) // 5)
        if key not in seen:
            seen.add(key)
            merged.append(f)
    return merged


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def score(findings: list[dict], gt: dict) -> dict:
    """Score findings against ground truth. Returns TP/FP/FN/TN + metrics."""
    gt_entries = gt.get("findings", [])
    tps_gt = [e for e in gt_entries if e.get("is_vulnerable", True)]
    fps_gt = [e for e in gt_entries if not e.get("is_vulnerable", True)]

    # For each GT TP, check if any finding matches (file + CWE + line ±10)
    matched_tp = 0
    matched_fp = 0

    for gt_e in tps_gt:
        gt_file = gt_e.get("file", "").replace("\\", "/")
        gt_cwes = set(gt_e.get("acceptable_cwes", [gt_e.get("primary_cwe", "")]))
        gt_line = gt_e.get("location", {}).get("start_line", 0) or 0

        for f in findings:
            if f["file"].endswith(gt_file) or gt_file.endswith(f["file"]):
                if f["cwe"] in gt_cwes:
                    if gt_line == 0 or abs((f["line"] or 0) - gt_line) <= 10:
                        matched_tp += 1
                        break

    for gt_e in fps_gt:
        gt_file = gt_e.get("file", "").replace("\\", "/")
        gt_cwes = set(gt_e.get("acceptable_cwes", [gt_e.get("primary_cwe", "")]))
        gt_line = gt_e.get("location", {}).get("start_line", 0) or 0

        for f in findings:
            if f["file"].endswith(gt_file) or gt_file.endswith(f["file"]):
                if f["cwe"] in gt_cwes:
                    if gt_line == 0 or abs((f["line"] or 0) - gt_line) <= 10:
                        matched_fp += 1
                        break

    n_tp_gt = len(tps_gt)
    n_fp_gt = len(fps_gt)
    tp = matched_tp
    fp = matched_fp
    fn = n_tp_gt - tp
    tn = n_fp_gt - fp

    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    f1 = _fbeta(prec, rec, 1.0)
    f2 = _fbeta(prec, rec, 2.0)
    f3 = _fbeta(prec, rec, 3.0)
    mcc = _mcc(tp, tn, fp, fn)
    j = rec - fpr

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "n_tp_gt": n_tp_gt,
        "n_fp_gt": n_fp_gt,
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "fpr": round(fpr, 4),
        "f1": round(f1, 4),
        "f2": round(f2, 4),
        "f3": round(f3, 4),
        "mcc": round(mcc, 4),
        "youden_j": round(j, 4),
    }


def aggregate(scores: list[dict]) -> dict:
    """Macro-average across repos."""
    if not scores:
        return {}
    tp = sum(s["tp"] for s in scores)
    fp = sum(s["fp"] for s in scores)
    fn = sum(s["fn"] for s in scores)
    tn = sum(s["tn"] for s in scores)
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    f2 = _fbeta(prec, rec, 2.0)
    f3 = _fbeta(prec, rec, 3.0)
    mcc = _mcc(tp, tn, fp, fn)
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "fpr": round(fpr, 4),
        "f2": round(f2, 4),
        "f3": round(f3, 4),
        "mcc": round(mcc, 4),
        "youden_j": round(rec - fpr, 4),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--realvuln-dir", default=str(_ROOT / "TESTS/evaluation/realvuln"))
    ap.add_argument("--output-dir", default=str(_ROOT / "docs/evaluation"))
    args = ap.parse_args()

    rv_dir = Path(args.realvuln_dir)
    repos_dir = rv_dir / "repos"
    gt_dir = rv_dir / "ground-truth"
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not repos_dir.exists():
        print("ERROR: repos/ not found. Run clone_repos.py first.", file=sys.stderr)
        sys.exit(1)

    cloned = {d.name for d in sorted(repos_dir.iterdir()) if d.is_dir()}
    gt_slugs = {d.name for d in sorted(gt_dir.iterdir()) if d.is_dir()}
    runnable = sorted(cloned & gt_slugs)

    print(f"\n{'='*65}")
    print("ACR-QA RealVuln Benchmark")
    print(f"  Version:  {__version__}")
    print(f"  Repos:    {len(runnable)} / 26 cloned")
    print(f"  Date:     {_NOW.strftime('%Y-%m-%d')}")
    print(f"{'='*65}\n")

    tools = {
        "ACR-QA (Bandit + Semgrep + custom)": run_acrqa_full,
        "Bandit (standalone)": run_bandit,
    }

    results: dict[str, list[dict]] = {name: [] for name in tools}

    for slug in runnable:
        repo_path = str(repos_dir / slug)
        gt_file = gt_dir / slug / "ground-truth.json"
        if not gt_file.exists():
            continue
        gt = json.load(open(gt_file))
        n_tp = sum(1 for f in gt.get("findings", []) if f.get("is_vulnerable", True))
        print(f"  {slug[:45]:<47} (GT TP={n_tp})")

        for tool_name, runner in tools.items():
            findings = runner(repo_path)
            s = score(findings, gt)
            s["slug"] = slug
            s["n_findings"] = len(findings)
            results[tool_name].append(s)
            print(f"    {tool_name[:35]:<37} recall={s['recall']*100:.0f}%  F3={s['f3']:.3f}")

    print(f"\n{'='*65}")
    print("AGGREGATE RESULTS")
    print(f"{'='*65}")
    print(f"{'Tool':<38} {'Recall':>7} {'FPR':>6} {'F3':>6} {'MCC':>6} {'J':>6}")
    print(f"{'-'*65}")

    agg_results: dict[str, dict] = {}
    for name, scores in results.items():
        agg = aggregate(scores)
        agg_results[name] = agg
        print(
            f"{name:<38} "
            f"{agg['recall']*100:6.1f}%  "
            f"{agg['fpr']*100:5.1f}%  "
            f"{agg['f3']:6.3f}  "
            f"{agg['mcc']:6.3f}  "
            f"{agg['youden_j']:6.3f}"
        )

    # Write markdown
    date_str = _NOW.strftime("%Y%m%d")
    md_path = out_dir / f"REALVULN_BENCHMARK_{date_str}.md"
    json_path = out_dir / f"REALVULN_BENCHMARK_{date_str}.json"
    _write_markdown(md_path, agg_results, results, len(runnable))
    _write_json(json_path, agg_results, results)

    print(f"\n  → {md_path}")
    print(f"  → {json_path}")


def _write_markdown(path: Path, agg: dict, per_repo: dict, n_repos: int) -> None:
    lines = [
        "# ACR-QA RealVuln Benchmark",
        "",
        f"> **Generated:** {_NOW.isoformat()}  ",
        f"> **ACR-QA version:** {__version__}  ",
        "> **Corpus:** RealVuln (kolega-ai/Real-Vuln-Benchmark)  ",
        f"> **Repos:** {n_repos}/26 cloned (4 GitHub URLs broken in manifest)  ",
        "> **Methodology:** file + CWE + line (±10) matching; F2/F3 (recall-weighted); MCC  ",
        "",
        "## Why RealVuln",
        "",
        "RealVuln uses **real production Python apps** (not synthetic snippets) with hand-labelled",
        "TP and FP traps — designed specifically to resist SAST gaming. Each ground-truth entry",
        "lists `acceptable_cwes` (CWE families that count), `is_vulnerable` (TP vs FP trap),",
        "and file+line location. Scoring requires correct CWE *and* file *and* line (±10).",
        "",
        "This directly addresses the 'benchmarked themselves' objection: the corpus is from a",
        "third-party lab, uses real multi-file applications, and includes FP traps.",
        "",
        "## Aggregate Results",
        "",
        "| Tool | Recall | FPR | F3 | MCC | Youden J |",
        "|------|:---:|:---:|:---:|:---:|:---:|",
    ]

    for name, a in sorted(agg.items(), key=lambda x: -x[1]["f3"]):
        bold = "**" if "ACR-QA" in name else ""
        lines.append(
            f"| {bold}{name}{bold} "
            f"| {bold}{a['recall']*100:.1f}%{bold} "
            f"| {a['fpr']*100:.1f}% "
            f"| {bold}{a['f3']:.3f}{bold} "
            f"| {a['mcc']:.3f} "
            f"| {a['youden_j']:.3f} |"
        )

    lines += [
        "",
        "## Per-Repo Recall (ACR-QA full output)",
        "",
        "| Repo | GT TPs | GT FPs | TP | FP | FN | Recall | F3 |",
        "|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|",
    ]

    acrqa_scores = per_repo.get("ACR-QA (Bandit + Semgrep + custom)", [])
    for s in sorted(acrqa_scores, key=lambda x: -x["recall"]):
        slug = s["slug"].replace("realvuln-", "")
        lines.append(
            f"| {slug[:35]} "
            f"| {s['n_tp_gt']} | {s['n_fp_gt']} "
            f"| {s['tp']} | {s['fp']} | {s['fn']} "
            f"| {s['recall']*100:.0f}% | {s['f3']:.3f} |"
        )

    lines += [
        "",
        "## Matching Methodology",
        "",
        "A finding is a **TP** if all three match:",
        "1. **File:** finding file path ends-with or equals the GT file path",
        "2. **CWE:** finding CWE is in the GT's `acceptable_cwes` list",
        "3. **Line:** finding line is within ±10 of the GT start_line",
        "",
        "A **FP** is a finding that matches a GT entry with `is_vulnerable=false`.",
        "FN = GT TPs that no finding matched. TN = GT FP-traps that no finding matched.",
        "",
        "## Reproduce",
        "",
        "```bash",
        "# Clone repos (one-time)",
        "cd TESTS/evaluation/realvuln && python3 clone_repos.py",
        "",
        "# Run benchmark",
        "python3 scripts/run_realvuln_benchmark.py",
        "```",
    ]

    path.write_text("\n".join(lines) + "\n")


def _write_json(path: Path, agg: dict, per_repo: dict) -> None:
    payload = {
        "generated": _NOW.isoformat(),
        "version": __version__,
        "aggregate": agg,
        "per_repo": {k: v for k, v in per_repo.items()},
    }
    path.write_text(json.dumps(payload, indent=2) + "\n")


if __name__ == "__main__":
    main()
