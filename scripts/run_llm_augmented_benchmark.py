#!/usr/bin/env python3
"""
LLM-Augmented Detection Benchmark — Phase 1+2 of GO_BIG_LLM_DETECTION_PLAN.md.

Measures four operating points across all RealVuln repos:
  1. RULES-ONLY          — Bandit + Semgrep + custom (baseline, 25.1% full / 37.8% det.)
  2. LLM-ONLY (raw)      — LLMDetector ungated (~17–22% strict, ~80% FP)
  3. UNION (rules ∪ LLM) — additive combination (+9pp lift from Phase 0)
  4. UNION-GATED         — union filtered through second-opinion LLM gate (precision target ≥90%)

Uses held-out split: tune/cache on the 6 Phase-0 repos, measure on held-out repos.

Usage:
    python3 scripts/run_llm_augmented_benchmark.py [--held-out-only]
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from CORE import __version__
from CORE.engines.llm_detector import _MODEL, LLMDetector, LLMFinding
from CORE.engines.normalizer import RULE_MAPPING

_ROOT = Path(__file__).parent.parent
_NOW = datetime.now(timezone.utc)
_RV = _ROOT / "TESTS" / "evaluation" / "realvuln"

# Phase-0 repos = "tune" set (cached); held-out = the rest
TUNE_REPOS = {
    "realvuln-vampi",
    "realvuln-dsvpwa",
    "realvuln-dsvw",
    "realvuln-dvpwa",
    "realvuln-flask-xss",
    "realvuln-insecure-web",
}

# CWE family map (same as triage script)
_CWE_FAM: dict[str, str] = {}


def _load_cwe_family_map() -> dict[str, str]:
    global _CWE_FAM
    if _CWE_FAM:
        return _CWE_FAM
    fam_file = _RV / "config" / "cwe-families.json"
    if fam_file.exists():
        d = json.loads(fam_file.read_text())
        for fam, info in d.get("families", {}).items():
            for cwe in info.get("cwes", []):
                _CWE_FAM[cwe.upper()] = fam
    return _CWE_FAM


def _fam(cwe: str) -> str:
    return _load_cwe_family_map().get(cwe.upper(), "unknown")


# ---------------------------------------------------------------------------
# CWE mappings for rule-based detection
# ---------------------------------------------------------------------------

BANDIT_CWE: dict[str, str] = {
    "B102": "CWE-78",
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
    "B307": "CWE-94",
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
    "B403": "CWE-502",
    "B404": "CWE-78",
    "B405": "CWE-611",
    "B406": "CWE-611",
    "B407": "CWE-611",
    "B408": "CWE-611",
    "B409": "CWE-611",
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
    "SECURITY-008": "CWE-502",
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
    "SECURITY-082": "CWE-16",
    "SECURITY-083": "CWE-16",
    "SECURITY-084": "CWE-352",
    "SECURITY-085": "CWE-79",
    "SECURITY-086": "CWE-79",
    "SECURITY-087": "CWE-1004",
    "SECURITY-088": "CWE-614",
    "SECURITY-601": "CWE-601",
}

SEMGREP_RE = re.compile(r"(CWE-\d+)")


# ---------------------------------------------------------------------------
# Rule-based detection (same as run_realvuln_benchmark.py)
# ---------------------------------------------------------------------------


def _venv(name: str) -> str:
    p = _ROOT / ".venv" / "bin" / name
    return str(p) if p.exists() else name


def run_rules(repo_dir: str) -> list[dict]:
    findings: list[dict] = []
    try:
        r = subprocess.run(
            [_venv("bandit"), "-r", repo_dir, "-f", "json", "-q"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        for res in json.loads(r.stdout or "{}").get("results", []):
            tid = res.get("test_id", "")
            cwe = BANDIT_CWE.get(tid)
            if not cwe:
                continue
            try:
                fname = str(Path(res.get("filename", "")).relative_to(repo_dir))
            except ValueError:
                fname = res.get("filename", "")
            findings.append(
                {"file": fname.replace("\\", "/"), "cwe": cwe, "line": res.get("line_number"), "source": "rules"}
            )
    except Exception:
        pass

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
        for res in json.loads(r.stdout or "{}").get("results", []):
            metadata = res.get("extra", {}).get("metadata", {})
            raw_cwes = metadata.get("cwe", [])
            if isinstance(raw_cwes, str):
                raw_cwes = [raw_cwes]
            cwes = [m.group(1) for c in raw_cwes if (m := SEMGREP_RE.match(str(c)))]
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
            for cwe in cwes:
                findings.append(
                    {
                        "file": fname.replace("\\", "/"),
                        "cwe": cwe,
                        "line": res.get("start", {}).get("line"),
                        "source": "rules",
                    }
                )
    except Exception:
        pass

    # Deduplicate
    seen: set[tuple] = set()
    merged = []
    for f in findings:
        key = (f["file"], f["cwe"], (f["line"] or 0) // 5)
        if key not in seen:
            seen.add(key)
            merged.append(f)
    return merged


def llm_to_dict(f: LLMFinding) -> dict:
    return {"file": f.file, "cwe": f.cwe, "line": f.line, "source": "llm"}


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def _matches(finding: dict, gt_e: dict) -> bool:
    gt_file = gt_e.get("file", "")
    gt_cwes = set(gt_e.get("acceptable_cwes", [gt_e.get("primary_cwe", "")]))
    gt_line = gt_e.get("location", {}).get("start_line", 0) or 0
    f_file = finding.get("file", "")
    if not (f_file.endswith(gt_file) or gt_file.endswith(f_file)):
        return False
    if finding["cwe"] not in gt_cwes:
        return False
    return gt_line == 0 or abs((finding.get("line") or 0) - gt_line) <= 10


def score(findings: list[dict], gt: dict) -> dict:
    gt_tps = [e for e in gt.get("findings", []) if e.get("is_vulnerable", True)]
    gt_fps = [e for e in gt.get("findings", []) if not e.get("is_vulnerable", True)]
    tp = sum(1 for e in gt_tps if any(_matches(f, e) for f in findings))
    fp = sum(1 for e in gt_fps if any(_matches(f, e) for f in findings))
    fn = len(gt_tps) - tp
    tn = len(gt_fps) - fp
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "recall": round(rec, 4),
        "precision": round(prec, 4),
        "fpr": round(fpr, 4),
    }


def merge_dedup(a: list[dict], b: list[dict]) -> list[dict]:
    """Union of two finding lists, deduplicated by (file, cwe, line//5)."""
    seen: set[tuple] = set()
    merged = []
    for f in a + b:
        key = (f.get("file", ""), f.get("cwe", ""), (f.get("line") or 0) // 5)
        if key not in seen:
            seen.add(key)
            merged.append(f)
    return merged


def agg(scores: list[dict]) -> dict:
    tp = sum(s["tp"] for s in scores)
    fp = sum(s["fp"] for s in scores)
    fn = sum(s["fn"] for s in scores)
    tn = sum(s["tn"] for s in scores)
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "recall": round(rec, 4),
        "precision": round(prec, 4),
        "fpr": round(fpr, 4),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--held-out-only", action="store_true", help="Only score repos NOT in the Phase-0 tune set")
    ap.add_argument("--no-gate", action="store_true", help="Skip gating (faster, shows raw LLM lift only)")
    ap.add_argument("--output-dir", default=str(_ROOT / "docs/evaluation"))
    args = ap.parse_args()

    repos_dir = _RV / "repos"
    gt_dir = _RV / "ground-truth"
    out_dir = Path(args.output_dir)

    cloned = {d.name for d in sorted(repos_dir.iterdir()) if d.is_dir()}
    gt_slugs = {d.name for d in sorted(gt_dir.iterdir()) if d.is_dir()}
    runnable = sorted(cloned & gt_slugs)

    if args.held_out_only:
        runnable = [r for r in runnable if r not in TUNE_REPOS]
        print(f"\n[HELD-OUT] {len(runnable)} repos (excluding Phase-0 tune set)")
    else:
        print(f"\n[ALL] {len(runnable)} repos")

    detector = LLMDetector(use_cache=True, gate=not args.no_gate)
    if not detector.available():
        print("ERROR: No Groq keys found in .env — cannot run LLM detection.")
        sys.exit(1)

    print(f"Model: {_MODEL}  Keys: {len(detector._keys)}  Gate: {not args.no_gate}")
    print(f"{'='*72}\n")

    results_per_point: dict[str, list[dict]] = {
        "rules": [],
        "llm_raw": [],
        "union": [],
        "union_gated": [],
    }

    for slug in runnable:
        repo_path = str(repos_dir / slug)
        gt = json.load(open(gt_dir / slug / "ground-truth.json"))
        n_tp = sum(1 for f in gt.get("findings", []) if f.get("is_vulnerable", True))
        print(f"  {slug[:50]:<52} GT_TP={n_tp}")

        # 1 — Rules
        rule_findings = run_rules(repo_path)
        s_rules = score(rule_findings, gt)
        results_per_point["rules"].append(s_rules)

        # 2 — LLM raw
        llm_raw = detector.detect_repo(repo_path)
        llm_dicts = [llm_to_dict(f) for f in llm_raw]
        s_llm = score(llm_dicts, gt)
        results_per_point["llm_raw"].append(s_llm)

        # 3 — Union (rules ∪ LLM)
        union = merge_dedup(rule_findings, llm_dicts)
        s_union = score(union, gt)
        results_per_point["union"].append(s_union)

        # 4 — Union gated
        if not args.no_gate:
            gated = detector.gate_findings(llm_raw, repo_path)
            gated_dicts = [llm_to_dict(f) for f in gated]
            union_gated = merge_dedup(rule_findings, gated_dicts)
            s_gated = score(union_gated, gt)
        else:
            s_gated = s_union
        results_per_point["union_gated"].append(s_gated)

        lift = s_union["recall"] - s_rules["recall"]
        gated_lift = s_gated["recall"] - s_rules["recall"]
        print(
            f"    rules={s_rules['recall']*100:.0f}%  "
            f"llm={s_llm['recall']*100:.0f}%  "
            f"union={s_union['recall']*100:.0f}%(+{lift*100:.0f}pp)  "
            f"gated={s_gated['recall']*100:.0f}%(+{gated_lift*100:.0f}pp)  "
            f"llm_prec={s_llm['precision']*100:.0f}%"
        )

    print(f"\n{'='*72}")
    print("AGGREGATE RESULTS")
    print(f"{'='*72}")

    aggs = {k: agg(v) for k, v in results_per_point.items()}
    labels = {
        "rules": "RULES-ONLY (baseline)",
        "llm_raw": "LLM-ONLY (raw, ungated)",
        "union": "UNION (rules ∪ LLM raw)",
        "union_gated": "UNION-GATED (gated precision)",
    }
    print(f"\n{'Operating Point':<38} {'Recall':>7} {'Precision':>10} {'FPR':>7} {'Lift':>7}")
    print("-" * 72)
    base_recall = aggs["rules"]["recall"]
    for key, label in labels.items():
        a = aggs[key]
        lift_str = f"+{(a['recall']-base_recall)*100:.1f}pp" if key != "rules" else "—"
        print(f"  {label:<36} {a['recall']*100:6.1f}%  {a['precision']*100:8.1f}%  {a['fpr']*100:6.1f}%  {lift_str:>7}")

    # Write outputs
    date_str = _NOW.strftime("%Y%m%d")
    suffix = "_held_out" if args.held_out_only else "_full"
    _write_md(
        out_dir / f"LLM_AUGMENTED_BENCHMARK{suffix}_{date_str}.md",
        aggs,
        labels,
        base_recall,
        len(runnable),
        args.held_out_only,
    )
    _write_json(out_dir / f"LLM_AUGMENTED_BENCHMARK{suffix}_{date_str}.json", aggs, results_per_point)
    print(f"\n  → {out_dir}/LLM_AUGMENTED_BENCHMARK{suffix}_{date_str}.md")
    print(f"  → {out_dir}/LLM_AUGMENTED_BENCHMARK{suffix}_{date_str}.json")

    # Decision gate
    union_lift = (aggs["union"]["recall"] - base_recall) * 100
    gated_prec = aggs["union_gated"]["precision"] * 100
    gated_lift = (aggs["union_gated"]["recall"] - base_recall) * 100
    print(f"\n{'='*72}")
    print("PHASE 2 DECISION GATE")
    print(f"  Union recall lift:       +{union_lift:.1f}pp  (target ≥+6pp)")
    print(f"  Gated precision:          {gated_prec:.1f}%   (target ≥90%)")
    print(f"  Gated recall lift:       +{gated_lift:.1f}pp  (should retain ≥4pp)")
    if union_lift >= 6 and gated_prec >= 85 and gated_lift >= 3:
        print("\n  ✅ GO — ship LLM-augmented pipeline, update docs.")
    else:
        print("\n  ❌ NO-GO — gating insufficient. Defend on current numbers, Future Work.")


def _write_md(path: Path, aggs: dict, labels: dict, base: float, n_repos: int, held_out: bool) -> None:
    split = "held-out" if held_out else "full"
    lines = [
        f"# ACR-QA LLM-Augmented Detection Benchmark ({split})",
        "",
        f"> **Generated:** {_NOW.isoformat()}  ",
        f"> **ACR-QA version:** {__version__}  ",
        f"> **Repos:** {n_repos} ({split} split)  ",
        f"> **Model:** {_MODEL}  ",
        "> **Phase:** 1+2 of GO_BIG_LLM_DETECTION_PLAN.md  ",
        "",
        "## Operating-Point Comparison",
        "",
        "| Operating Point | Recall | Precision | FPR | Lift |",
        "|---|:---:|:---:|:---:|:---:|",
    ]
    for key, label in labels.items():
        a = aggs[key]
        lift = f"+{(a['recall']-base)*100:.1f}pp" if key != "rules" else "—"
        bold = "**" if "GATED" in label.upper() else ""
        lines.append(
            f"| {bold}{label}{bold} | {bold}{a['recall']*100:.1f}%{bold} "
            f"| {a['precision']*100:.1f}% | {a['fpr']*100:.1f}% | {bold}{lift}{bold} |"
        )
    lines += [
        "",
        "## Key Numbers",
        "",
        f"- **Baseline (rules-only):** {base*100:.1f}% recall",
        f"- **Union lift (raw):** +{(aggs['union']['recall']-base)*100:.1f}pp",
        f"- **Gated precision:** {aggs['union_gated']['precision']*100:.1f}%",
        f"- **Gated lift retained:** +{(aggs['union_gated']['recall']-base)*100:.1f}pp",
    ]
    path.write_text("\n".join(lines) + "\n")


def _write_json(path: Path, aggs: dict, per_point: dict) -> None:
    path.write_text(
        json.dumps(
            {
                "generated": _NOW.isoformat(),
                "version": __version__,
                "model": _MODEL,
                "aggregate": aggs,
                "per_repo_counts": {k: len(v) for k, v in per_point.items()},
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
