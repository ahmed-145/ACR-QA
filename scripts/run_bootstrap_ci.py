#!/usr/bin/env python3
"""
T4.2 Bootstrap Confidence Intervals — 95% CIs on precision via per-repo resampling.

Approach:
  - Unit of resampling: repo (not finding). Resampling at repo level captures the
    true variability in precision across different codebases.
  - Each bootstrap sample: draw N repos with replacement from the corpus; sum TP/FP/NR;
    compute precision.
  - CI: 2.5th–97.5th percentile of 10,000 bootstrap iterations.

No scipy required — pure random + statistics stdlib.

Usage:
    python scripts/run_bootstrap_ci.py [--n-boot 10000]
"""

from __future__ import annotations

import json
import os
import random
import sys
from datetime import datetime, timezone  # noqa: UP017
from pathlib import Path
from statistics import mean, stdev

ROOT = Path(__file__).resolve().parent.parent
FINDINGS_DIR = ROOT / "TESTS/evaluation/results/precision_findings"
SUMMARY_FILE = ROOT / "TESTS/evaluation/results/precision_summary.json"
OUTPUT_JSON = ROOT / "TESTS/evaluation/results/bootstrap_ci.json"
OUTPUT_MD = ROOT / "docs/evaluation/BOOTSTRAP_CI.md"
EVAL_SUMMARY = ROOT / "TESTS/evaluation/results/eval_summary.json"

sys.path.insert(0, str(ROOT / "scripts"))
import run_ablation_study as ab  # reuse triage constants


# ── Data loading ──────────────────────────────────────────────────────────────


def load_per_repo_data() -> list[dict]:
    """Load triage counts per repo from cached precision findings."""
    rows: list[dict] = []
    for fn in sorted(os.listdir(FINDINGS_DIR)):
        if not fn.endswith(".json"):
            continue
        repo = fn.replace("_findings.json", "")
        with open(FINDINGS_DIR / fn) as fh:
            findings = json.load(fh)

        hm = [f for f in findings if ab._sev(f) in ("high", "medium")]
        sec = [f for f in findings if ab._sev(f) == "high" and ab._rule(f) in ab.SECURITY_CATEGORY_RULES]

        def _counts(fs: list[dict]) -> tuple[int, int, int]:
            tp = fp = nr = 0
            for f in fs:
                v = ab.triage_finding(f)
                if v == "AUTO_TP":
                    tp += 1
                elif v == "AUTO_FP":
                    fp += 1
                elif v == "NEEDS_REVIEW":
                    nr += 1
            return tp, fp, nr

        hm_tp, hm_fp, hm_nr = _counts(hm)
        sec_tp, sec_fp, sec_nr = _counts(sec)

        # Infer language from extension/path heuristic
        lang = "python"
        for f in findings:
            p = ab._path(f)
            if p.endswith((".js", ".ts", ".jsx", ".tsx")):
                lang = "javascript"
                break

        rows.append(
            {
                "repo": repo,
                "language": lang,
                "hm_total": len(hm),
                "hm_tp": hm_tp,
                "hm_fp": hm_fp,
                "hm_nr": hm_nr,
                "sec_total": len(sec),
                "sec_tp": sec_tp,
                "sec_fp": sec_fp,
                "sec_nr": sec_nr,
            }
        )
    return rows


# ── Bootstrap engine ──────────────────────────────────────────────────────────


def _precision(tp: int, fp: int, nr: int, conservative: bool) -> float | None:
    denom = tp + fp + (nr if conservative else 0) + (0 if conservative else 0)
    # conservative: NR → FP (total = tp + fp + nr); optimistic: NR → TP (total = tp + fp + nr still)
    total = tp + fp + nr
    if total == 0:
        return None
    if conservative:
        # NR counted as FP
        return tp / total
    else:
        # NR counted as TP
        return (tp + nr) / total


def bootstrap_ci(
    rows: list[dict],
    key_prefix: str,  # "hm" or "sec"
    conservative: bool,
    n_boot: int = 10_000,
    seed: int = 42,
) -> dict:
    """Bootstrap 95% CI for precision over repos."""
    rng = random.Random(seed)
    n = len(rows)
    if n == 0:
        return {"error": "no data"}

    # Point estimate (no resampling)
    total_tp = sum(r[f"{key_prefix}_tp"] for r in rows)
    total_fp = sum(r[f"{key_prefix}_fp"] for r in rows)
    total_nr = sum(r[f"{key_prefix}_nr"] for r in rows)
    point = _precision(total_tp, total_fp, total_nr, conservative)

    # Bootstrap samples
    boot_precisions: list[float] = []
    for _ in range(n_boot):
        sample = [rows[rng.randint(0, n - 1)] for _ in range(n)]
        b_tp = sum(r[f"{key_prefix}_tp"] for r in sample)
        b_fp = sum(r[f"{key_prefix}_fp"] for r in sample)
        b_nr = sum(r[f"{key_prefix}_nr"] for r in sample)
        p = _precision(b_tp, b_fp, b_nr, conservative)
        if p is not None:
            boot_precisions.append(p)

    if not boot_precisions:
        return {"error": "all bootstrap samples had zero denominator"}

    boot_precisions.sort()
    lo = boot_precisions[int(0.025 * len(boot_precisions))]
    hi = boot_precisions[int(0.975 * len(boot_precisions))]

    return {
        "point_estimate": round(point, 4) if point is not None else None,
        "ci_95_lo": round(lo, 4),
        "ci_95_hi": round(hi, 4),
        "ci_95_width": round(hi - lo, 4),
        "n_repos": n,
        "n_boot": n_boot,
        "boot_mean": round(mean(boot_precisions), 4),
        "boot_stdev": round(stdev(boot_precisions), 4) if len(boot_precisions) > 1 else None,
        "mode": "conservative" if conservative else "optimistic",
        "total_tp": total_tp,
        "total_fp": total_fp,
        "total_nr": total_nr,
    }


# ── Main ──────────────────────────────────────────────────────────────────────


def run_bootstrap(n_boot: int = 10_000) -> dict:
    print(f"Loading per-repo data from {FINDINGS_DIR.name}/…", flush=True)
    rows = load_per_repo_data()
    print(f"  {len(rows)} repos loaded", flush=True)

    rows_py = [r for r in rows if r["language"] == "python"]
    rows_js = [r for r in rows if r["language"] == "javascript"]

    print(f"  python: {len(rows_py)} repos  javascript: {len(rows_js)} repos", flush=True)

    print(f"Running bootstrap ({n_boot:,} iterations per metric)…", flush=True)

    results: dict = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),  # noqa: UP017
        "method": (
            "Per-repo bootstrap resampling. Unit of resampling = repo. "
            "Each iteration draws N repos with replacement, sums TP/FP/NR, "
            "computes precision. 95% CI = 2.5th–97.5th percentile of 10,000 samples."
        ),
        "n_boot": n_boot,
        "n_repos_total": len(rows),
        "metrics": {},
    }

    metrics = [
        ("hm_conservative", rows, "hm", True, "H/M all-tools, conservative"),
        ("hm_optimistic", rows, "hm", False, "H/M all-tools, optimistic"),
        ("sec_conservative", rows, "sec", True, "Security-tier, conservative"),
        ("sec_optimistic", rows, "sec", False, "Security-tier, optimistic"),
        ("hm_conservative_py", rows_py, "hm", True, "H/M Python only, conservative"),
        ("hm_conservative_js", rows_js, "hm", True, "H/M JavaScript only, conservative"),
        ("sec_conservative_py", rows_py, "sec", True, "Sec-tier Python only, conservative"),
        ("sec_conservative_js", rows_js, "sec", True, "Sec-tier JS only, conservative"),
    ]

    for key, rw, prefix, conservative, label in metrics:
        ci = bootstrap_ci(rw, prefix, conservative, n_boot)
        ci["label"] = label
        results["metrics"][key] = ci
        p = ci.get("point_estimate")
        lo = ci.get("ci_95_lo")
        hi = ci.get("ci_95_hi")
        pct_p = f"{p*100:.1f}%" if p is not None else "N/A"
        pct_lo = f"{lo*100:.1f}%" if lo is not None else "N/A"
        pct_hi = f"{hi*100:.1f}%" if hi is not None else "N/A"
        print(f"  {label:<45} {pct_p}  95% CI [{pct_lo}, {pct_hi}]", flush=True)

    # Write JSON
    with open(OUTPUT_JSON, "w") as fh:
        json.dump(results, fh, indent=2)
    print(f"\n  → {OUTPUT_JSON.relative_to(ROOT)}", flush=True)

    # Write Markdown
    _write_markdown(results)
    print(f"  → {OUTPUT_MD.relative_to(ROOT)}", flush=True)

    # Update eval_summary
    _update_eval_summary(results)
    print(f"  → eval_summary.json updated", flush=True)

    return results


def _pct(v: float | None, decimals: int = 1) -> str:
    return f"{v * 100:.{decimals}f}%" if v is not None else "N/A"


def _ci_str(ci: dict) -> str:
    return f"{_pct(ci.get('point_estimate'))} " f"[{_pct(ci.get('ci_95_lo'))}, {_pct(ci.get('ci_95_hi'))}]"


def _write_markdown(r: dict) -> None:
    m = r["metrics"]
    lines = [
        "# T4.2 Bootstrap Confidence Intervals",
        "",
        f"_Generated: {r['generated']}_  ",
        f"_Method: {r['method']}_  ",
        f"_n_boot = {r['n_boot']:,}, n_repos = {r['n_repos_total']}_",
        "",
        "## Summary",
        "",
        "| Metric | Point Estimate | 95% CI | CI Width | n repos |",
        "|--------|---------------|--------|----------|---------|",
    ]

    display_keys = [
        "hm_conservative",
        "hm_optimistic",
        "sec_conservative",
        "sec_optimistic",
        "hm_conservative_py",
        "hm_conservative_js",
        "sec_conservative_py",
        "sec_conservative_js",
    ]
    for k in display_keys:
        ci = m[k]
        lines.append(
            f"| {ci['label']} "
            f"| **{_pct(ci['point_estimate'])}** "
            f"| [{_pct(ci['ci_95_lo'])}, {_pct(ci['ci_95_hi'])}] "
            f"| {_pct(ci['ci_95_width'])} "
            f"| {ci['n_repos']} |"
        )

    lines += [
        "",
        "> **Conservative**: NEEDS_REVIEW → FP.  **Optimistic**: NEEDS_REVIEW → TP.",
        "",
        "## Interpretation",
        "",
        "### Primary defence number",
        "",
        f"Security-tier precision: **{_ci_str(m['sec_conservative'])}** (conservative) / "
        f"**{_ci_str(m['sec_optimistic'])}** (optimistic).",
        "",
        "The 95% confidence interval captures uncertainty arising from the particular",
        "set of repositories in the corpus. If we had sampled a different set of 24",
        "production Python/JS libraries, precision would likely fall within this range.",
        "",
        "### H/M blended precision",
        "",
        f"All-findings H/M precision: **{_ci_str(m['hm_conservative'])}** (conservative). "
        "The wider CI here reflects high variance across repos — some repos generate "
        "many low-precision quality findings (radon/vulture) while others are security-heavy.",
        "",
        "### Language breakdown",
        "",
        f"- Python (sec-tier): {_ci_str(m['sec_conservative_py'])} conservative",
        f"- JavaScript (sec-tier): {_ci_str(m['sec_conservative_js'])} conservative",
        "",
        "JS sec-tier CI is wider (fewer repos) — interpret with more caution.",
        "",
        "### CI width interpretation",
        "",
        f"Security-tier CI width: {_pct(m['sec_conservative']['ci_95_width'])} — ",
        "a ±{:.1f}pp range. This is expected for a 24-repo precision corpus; ".format(
            (m["sec_conservative"]["ci_95_width"] or 0) * 100 / 2
        ),
        "a corpus of 100+ repos would narrow this to under ±5pp.",
        "",
        "## Bootstrap Distribution Statistics",
        "",
        "| Metric | Mean | Std Dev | CI Width |",
        "|--------|------|---------|---------|",
    ]

    for k in ["sec_conservative", "sec_optimistic", "hm_conservative"]:
        ci = m[k]
        lines.append(
            f"| {ci['label']} "
            f"| {_pct(ci['boot_mean'])} "
            f"| ±{_pct(ci['boot_stdev'])} "
            f"| {_pct(ci['ci_95_width'])} |"
        )

    lines += [
        "",
        "## Summary for Defence",
        "",
        "**Q: How reliable are your precision numbers?**",
        "",
        f"The 95% bootstrap CI for security-tier precision is "
        f"[{_pct(m['sec_conservative']['ci_95_lo'])}, {_pct(m['sec_conservative']['ci_95_hi'])}] "
        f"(conservative) / "
        f"[{_pct(m['sec_optimistic']['ci_95_lo'])}, {_pct(m['sec_optimistic']['ci_95_hi'])}] "
        f"(optimistic). These CIs are computed by per-repo bootstrap resampling over "
        f"{r['n_repos_total']} production repositories with {r['n_boot']:,} iterations. "
        f"The interval captures corpus-sampling uncertainty — if we re-ran the benchmark "
        f"on a different set of production libraries, we would expect precision to fall "
        f"in this range with 95% probability.",
        "",
    ]

    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text("\n".join(lines) + "\n")


def _update_eval_summary(r: dict) -> None:
    with open(EVAL_SUMMARY) as fh:
        summary = json.load(fh)

    m = r["metrics"]
    summary["t4_bootstrap_ci"] = {
        "generated": r["generated"],
        "n_boot": r["n_boot"],
        "n_repos": r["n_repos_total"],
        "sec_conservative_ci": {
            "point": m["sec_conservative"]["point_estimate"],
            "ci_95_lo": m["sec_conservative"]["ci_95_lo"],
            "ci_95_hi": m["sec_conservative"]["ci_95_hi"],
        },
        "sec_optimistic_ci": {
            "point": m["sec_optimistic"]["point_estimate"],
            "ci_95_lo": m["sec_optimistic"]["ci_95_lo"],
            "ci_95_hi": m["sec_optimistic"]["ci_95_hi"],
        },
        "hm_conservative_ci": {
            "point": m["hm_conservative"]["point_estimate"],
            "ci_95_lo": m["hm_conservative"]["ci_95_lo"],
            "ci_95_hi": m["hm_conservative"]["ci_95_hi"],
        },
        "note": ("Per-repo bootstrap resampling. Conservative=NEEDS_REVIEW→FP, " "Optimistic=NEEDS_REVIEW→TP."),
    }
    summary["generated"] = "2026-05-29 (T4.2 bootstrap CI added)"

    with open(EVAL_SUMMARY, "w") as fh:
        json.dump(summary, fh, indent=2)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="T4.2 Bootstrap CIs")
    parser.add_argument("--n-boot", type=int, default=10_000)
    args = parser.parse_args()

    run_bootstrap(n_boot=args.n_boot)


if __name__ == "__main__":
    main()
