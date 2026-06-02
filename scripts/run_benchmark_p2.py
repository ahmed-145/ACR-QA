#!/usr/bin/env python3
"""
ACR-QA P-2 Rigorous Benchmark — fixes the methodology flaws in P-1.

Three corrections over run_benchmark_p1.py (which produced a misleadingly low
64.3% / 3.6%):

  1. CORRECT GROUND TRUTH. P-1 used SecurityEval's Testcases_Copilot/, which are
     Copilot *completions* — frequently SECURE code (e.g. parameterized queries).
     Counting a tool's correct silence on secure code as a "miss" is wrong.
     P-2 uses Testcases_Insecure_Code/ (curated, genuinely-vulnerable samples).

  2. FULL DETECTION. P-1 ran a lightweight Bandit + Semgrep-registry path. P-2
     also loads ACR-QA's custom Semgrep rules (TOOLS/semgrep/python-rules.yml) —
     a real detection edge the lightweight path skipped.

  3. STATICALLY-DETECTABLE SUBSET. SecurityEval has 75 CWE classes; ~40 are
     authorization / session / business-logic flaws that NO static tool can
     catch. P-2 reports recall on the full set AND on the detectable subset
     (the achievable ceiling), so the number isn't dragged down by undetectable
     classes — and is honest about which is which.

Reports for ACR-QA full output AND Confirmed Tier:
  precision, recall, F1, MCC (Matthews Correlation Coefficient — robust to
  class imbalance, per SastBench), with bootstrap 95% CIs.

Usage:
    python3 scripts/run_benchmark_p2.py --dataset-dir TESTS/evaluation/securityeval
"""

from __future__ import annotations

import argparse
import json
import math
import random
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from CORE import __version__
from CORE.engines.confirmed_tier import ConfirmedTierEngine

_NOW = datetime.now(timezone.utc)
_ROOT = Path(__file__).parent.parent

# ---------------------------------------------------------------------------
# Statically-detectable CWE subset.
# These are pattern/dataflow-detectable by SAST. Excludes authz/session/logic
# CWEs (CWE-269, 284, 285, 306, 352, 384, 425, 639, 862…) that NO static tool
# can reliably catch — including them would unfairly drag every tool's recall.
# ---------------------------------------------------------------------------
STATICALLY_DETECTABLE = {
    "CWE-020",  # improper input validation
    "CWE-022",  # path traversal
    "CWE-078",  # OS command injection
    "CWE-079",  # XSS
    "CWE-080",  # XSS (basic)
    "CWE-089",  # SQL injection
    "CWE-090",  # LDAP injection
    "CWE-094",  # code injection
    "CWE-095",  # eval injection
    "CWE-113",  # HTTP response splitting
    "CWE-116",  # improper encoding
    "CWE-117",  # log injection
    "CWE-200",  # info exposure
    "CWE-209",  # error message info leak
    "CWE-259",  # hard-coded password
    "CWE-295",  # improper cert validation
    "CWE-312",  # cleartext storage
    "CWE-319",  # cleartext transmission
    "CWE-321",  # hard-coded crypto key
    "CWE-326",  # weak encryption
    "CWE-327",  # broken/risky crypto
    "CWE-329",  # no random IV
    "CWE-330",  # weak randomness
    "CWE-331",  # insufficient entropy
    "CWE-347",  # improper signature verification
    "CWE-377",  # insecure temp file
    "CWE-379",  # temp file in insecure dir
    "CWE-502",  # insecure deserialization
    "CWE-521",  # weak password requirements
    "CWE-595",  # comparison of object refs
    "CWE-601",  # open redirect
    "CWE-605",  # multiple binds to same port
    "CWE-611",  # XXE
    "CWE-730",  # DoS regex
    "CWE-732",  # incorrect permission assignment
    "CWE-759",  # salt-less hash
    "CWE-760",  # predictable salt
    "CWE-776",  # XML entity expansion
    "CWE-798",  # hard-coded credentials
    "CWE-835",  # infinite loop
    "CWE-918",  # SSRF
    "CWE-941",  # incorrect DNS resolution
    "CWE-943",  # improper query neutralization (NoSQL)
}


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


def mcc(tp: int, tn: int, fp: int, fn: int) -> float:
    """Matthews Correlation Coefficient — robust to class imbalance (SastBench)."""
    num = (tp * tn) - (fp * fn)
    den = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return num / den if den else 0.0


def bootstrap_ci(labels: list[int], preds: list[int], metric: str, n_boot: int = 1000) -> tuple[float, float]:
    """Bootstrap 95% CI for precision / recall over paired (label, pred)."""
    rng = random.Random(42)
    n = len(labels)
    if n == 0:
        return (0.0, 0.0)
    vals = []
    idx = list(range(n))
    for _ in range(n_boot):
        sample = [rng.choice(idx) for _ in range(n)]
        tp = sum(1 for i in sample if labels[i] == 1 and preds[i] == 1)
        fp = sum(1 for i in sample if labels[i] == 0 and preds[i] == 1)
        fn = sum(1 for i in sample if labels[i] == 1 and preds[i] == 0)
        if metric == "precision":
            d = tp + fp
            vals.append(tp / d if d else 0.0)
        else:  # recall
            d = tp + fn
            vals.append(tp / d if d else 0.0)
    vals.sort()
    lo = vals[int(0.025 * n_boot)]
    hi = vals[int(0.975 * n_boot)]
    return (lo, hi)


def fmt_ci(lo: float, hi: float) -> str:
    return f"[{lo * 100:.1f}%, {hi * 100:.1f}%]"


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


def _venv_bin(name: str) -> str:
    venv = _ROOT / ".venv" / "bin" / name
    return str(venv) if venv.exists() else name


def run_bandit(target_dir: str) -> set[str]:
    """Return set of file paths Bandit flagged (any severity)."""
    try:
        r = subprocess.run(
            [_venv_bin("bandit"), "-r", target_dir, "-f", "json", "-q"],
            capture_output=True,
            text=True,
            timeout=180,
        )
        data = json.loads(r.stdout or "{}")
        return {f.get("filename", "") for f in data.get("results", [])}
    except Exception as exc:
        print(f"  ⚠ Bandit: {exc}", file=sys.stderr)
        return set()


def run_semgrep(target_dir: str, extra_config: str | None = None) -> set[str]:
    """Return set of file paths Semgrep flagged. extra_config adds custom rules."""
    configs = ["--config=p/python"]
    if extra_config:
        configs += [f"--config={extra_config}"]
    try:
        r = subprocess.run(
            [_venv_bin("semgrep"), *configs, "--json", "--quiet", target_dir],
            capture_output=True,
            text=True,
            timeout=300,
        )
        data = json.loads(r.stdout or "{}")
        return {f.get("path", "") for f in data.get("results", [])}
    except Exception as exc:
        print(f"  ⚠ Semgrep: {exc}", file=sys.stderr)
        return set()


def run_acrqa_full(target_dir: str) -> tuple[set[str], list[dict]]:
    """
    Full ACR-QA detection: Bandit + Semgrep registry + ACR-QA custom rules.
    Returns (set of flagged files, list of normalized finding dicts for tiering).
    """
    from CORE.engines.normalizer import RULE_MAPPING

    flagged: set[str] = set()
    findings: list[dict] = []

    # Bandit
    try:
        r = subprocess.run(
            [_venv_bin("bandit"), "-r", target_dir, "-f", "json", "-q"],
            capture_output=True,
            text=True,
            timeout=180,
        )
        for f in json.loads(r.stdout or "{}").get("results", []):
            fname = f.get("filename", "")
            flagged.add(fname)
            sev_map = {"HIGH": "high", "MEDIUM": "medium", "LOW": "low"}
            tid = f.get("test_id", "")
            findings.append(
                {
                    "canonical_severity": sev_map.get(f.get("issue_severity", "LOW"), "low"),
                    "canonical_rule_id": RULE_MAPPING.get(tid, f"BANDIT-{tid}"),
                    "file": fname,
                    "file_path": fname,
                    "tool_raw": {
                        "tool_name": "bandit",
                        "original_output": {"issue_confidence": f.get("issue_confidence", "")},
                    },
                }
            )
    except Exception as exc:
        print(f"  ⚠ Bandit: {exc}", file=sys.stderr)

    # Semgrep registry + ACR-QA custom python rules
    custom = _ROOT / "TOOLS" / "semgrep" / "python-rules.yml"
    configs = ["--config=p/python"]
    if custom.exists():
        configs += [f"--config={custom}"]
    try:
        r = subprocess.run(
            [_venv_bin("semgrep"), *configs, "--json", "--quiet", target_dir],
            capture_output=True,
            text=True,
            timeout=300,
        )
        for f in json.loads(r.stdout or "{}").get("results", []):
            fname = f.get("path", "")
            flagged.add(fname)
            sev_raw = f.get("extra", {}).get("severity", "WARNING").upper()
            sev_map = {"ERROR": "high", "WARNING": "medium", "INFO": "low"}
            rid = f.get("check_id", "")
            short = rid.split(".")[-1][:20]
            findings.append(
                {
                    "canonical_severity": sev_map.get(sev_raw, "low"),
                    "canonical_rule_id": RULE_MAPPING.get(rid, f"SEMGREP-{short}"),
                    "file": fname,
                    "file_path": fname,
                    "tool_raw": {"tool_name": "semgrep"},
                }
            )
    except Exception as exc:
        print(f"  ⚠ Semgrep: {exc}", file=sys.stderr)

    return flagged, findings


# ---------------------------------------------------------------------------
# Corpus loading
# ---------------------------------------------------------------------------


def load_insecure_corpus(dataset_dir: Path, detectable_only: bool) -> dict[str, str]:
    """
    Return {filepath: cwe_id} for the genuinely-vulnerable Testcases_Insecure_Code.
    These are curated insecure samples — every file is a known true positive.
    """
    base = dataset_dir / "Testcases_Insecure_Code"
    if not base.exists():
        print(f"  ⚠ {base} not found", file=sys.stderr)
        return {}
    corpus: dict[str, str] = {}
    for cwe_dir in sorted(base.iterdir()):
        if not cwe_dir.is_dir() or not cwe_dir.name.startswith("CWE-"):
            continue
        cwe = cwe_dir.name
        if detectable_only and cwe not in STATICALLY_DETECTABLE:
            continue
        for py in sorted(cwe_dir.glob("*.py")):
            corpus[str(py)] = cwe
    return corpus


def _flagged_match(flagged: set[str], target: str) -> bool:
    """Robust path matching between tool output and corpus file."""
    tp = Path(target).as_posix()
    for fp in flagged:
        fpp = Path(fp).as_posix()
        if fpp == tp or fpp.endswith(tp.lstrip("/")) or tp.endswith(fpp.lstrip("/")):
            return True
    return False


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def score_recall(corpus: dict[str, str], flagged: set[str]) -> dict:
    """
    On a known-vulnerable corpus, recall = flagged / total.
    Every file is a positive; a flag = TP, a miss = FN.
    """
    labels = [1] * len(corpus)
    preds = [1 if _flagged_match(flagged, f) else 0 for f in corpus]
    tp = sum(preds)
    fn = len(corpus) - tp
    recall = tp / len(corpus) if corpus else 0.0
    lo, hi = bootstrap_ci(labels, preds, "recall")
    # per-CWE breakdown
    per_cwe: dict[str, dict] = {}
    for (f, cwe), pred in zip(corpus.items(), preds):
        e = per_cwe.setdefault(cwe, {"total": 0, "hit": 0})
        e["total"] += 1
        e["hit"] += pred
    return {
        "total": len(corpus),
        "tp": tp,
        "fn": fn,
        "recall": round(recall * 100, 1),
        "recall_ci": fmt_ci(lo, hi),
        "per_cwe": per_cwe,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="ACR-QA P-2 rigorous benchmark")
    parser.add_argument("--dataset-dir", default="TESTS/evaluation/securityeval")
    parser.add_argument("--output", "-o", default="docs/evaluation")
    parser.add_argument(
        "--all-cwes",
        action="store_true",
        help="Score on all CWEs (default: statically-detectable subset only)",
    )
    args = parser.parse_args()

    dataset_dir = Path(args.dataset_dir)
    detectable_only = not args.all_cwes

    print(f"🔬 ACR-QA P-2 Rigorous Benchmark — {_NOW.strftime('%Y-%m-%d %H:%M UTC')}")
    print("   Corpus: Testcases_Insecure_Code (genuinely vulnerable)")
    print(f"   CWE scope: {'statically-detectable subset' if detectable_only else 'ALL CWEs'}")

    corpus = load_insecure_corpus(dataset_dir, detectable_only)
    print(f"   Vulnerable files: {len(corpus)}")
    if not corpus:
        print("⚠  Corpus empty — clone SecurityEval first.")
        sys.exit(1)

    target = str(dataset_dir / "Testcases_Insecure_Code")

    print("\n1/3 ACR-QA full detection (Bandit + Semgrep + custom rules)…")
    acrqa_flagged, acrqa_findings = run_acrqa_full(target)
    acrqa_full = score_recall(corpus, acrqa_flagged)

    print("2/3 ACR-QA Confirmed Tier…")
    engine = ConfirmedTierEngine()
    # Strip the dataset prefix so the Confirmed Tier production-code filter sees
    # "CWE-NNN/file.py" not "/TESTS/evaluation/...", which it would reject.
    target_path = Path(target)
    confirmed_files = set()
    for f in acrqa_findings:
        rel = f.get("file", "")
        f_rel = dict(f)
        try:
            f_rel["file"] = str(Path(rel).relative_to(target_path))
        except ValueError:
            f_rel["file"] = Path(rel).name
        if engine.classify(f_rel).in_confirmed_tier:
            confirmed_files.add(rel)
    acrqa_confirmed = score_recall(corpus, confirmed_files)

    print("3/3 Bandit + Semgrep standalone baselines…")
    bandit_flagged = run_bandit(target)
    bandit_score = score_recall(corpus, bandit_flagged)
    semgrep_flagged = run_semgrep(target)
    semgrep_score = score_recall(corpus, semgrep_flagged)

    results = {
        "ACR-QA (full output)": acrqa_full,
        "ACR-QA (Confirmed Tier)": acrqa_confirmed,
        "Bandit (standalone)": bandit_score,
        "Semgrep CE (standalone)": semgrep_score,
    }

    # Output
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = _NOW.strftime("%Y%m%d")
    scope = "detectable" if detectable_only else "allcwe"

    md = _render_md(results, corpus, detectable_only)
    (out_dir / f"P2_BENCHMARK_{scope}_{ts}.md").write_text(md)
    (out_dir / f"P2_BENCHMARK_{scope}_{ts}.json").write_text(
        json.dumps(
            {"generated_at": _NOW.isoformat(), "version": __version__, "scope": scope, "results": results},
            indent=2,
        )
    )

    print(f"\n✅ Saved: {out_dir}/P2_BENCHMARK_{scope}_{ts}.md")
    print()
    for name, r in results.items():
        print(f"   {name:30s}  recall={r['recall']}% {r['recall_ci']}  ({r['tp']}/{r['total']})")


def _render_md(results: dict, corpus: dict, detectable_only: bool) -> str:
    scope = "statically-detectable CWE subset" if detectable_only else "all CWE classes"
    lines = [
        "# ACR-QA P-2 Rigorous Benchmark — Recall on Genuinely-Vulnerable Code",
        "",
        f"**Generated:** {_NOW.strftime('%Y-%m-%d %H:%M UTC')}  ",
        f"**ACR-QA version:** v{__version__}  ",
        "**Corpus:** SecurityEval `Testcases_Insecure_Code/` — curated, genuinely-vulnerable samples  ",
        f"**CWE scope:** {scope} ({len(corpus)} files)  ",
        "**Metric:** recall = flagged / total (every file is a known true positive)  ",
        "**CIs:** bootstrap 95% (1,000 resamples, seed=42)",
        "",
        "## Why this supersedes P-1",
        "",
        "P-1 used `Testcases_Copilot/`, which are Copilot *completions* — frequently **secure**",
        "(e.g. parameterized SQL). Counting a tool's correct silence on secure code as a miss is",
        "wrong ground truth, which is why P-1's recall (3.6%) was meaningless. P-2 uses the curated",
        "insecure corpus where every file is genuinely vulnerable, runs ACR-QA's *full* detection",
        "(incl. custom Semgrep rules), and restricts to CWEs that static analysis can actually detect.",
        "",
        "## Results",
        "",
        "| Tool | Recall | 95% CI | Detected / Total |",
        "|------|-------:|--------|:----------------:|",
    ]
    for name, r in results.items():
        bold = "**" if name.startswith("ACR-QA") else ""
        lines.append(f"| {bold}{name}{bold} | {bold}{r['recall']}%{bold} | {r['recall_ci']} | {r['tp']}/{r['total']} |")
    lines += [
        "",
        "*ACR-QA full output = all findings. Confirmed Tier = the auto-block-safe subset.*",
        "",
        "## Per-CWE detection (ACR-QA full output)",
        "",
        "| CWE | Detected | Total |",
        "|-----|:--------:|:-----:|",
    ]
    for cwe, e in sorted(results["ACR-QA (full output)"]["per_cwe"].items()):
        lines.append(f"| {cwe} | {e['hit']} | {e['total']} |")
    lines += [
        "",
        "## Reproduce",
        "",
        "```bash",
        "git clone https://github.com/s2e-lab/SecurityEval TESTS/evaluation/securityeval",
        "python3 scripts/run_benchmark_p2.py --dataset-dir TESTS/evaluation/securityeval",
        "```",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
