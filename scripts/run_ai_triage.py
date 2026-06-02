#!/usr/bin/env python3
"""
Lever 3 — AI triage of NEEDS_REVIEW security-tier findings.

Calls Groq (llama-3.3-70b) on each remaining NEEDS_REVIEW finding in the
security tier. Accepts the AI verdict only under a conservative rule:
    - Both calls agree FP  → reclassify to AUTO_FP
    - Both calls agree TP  → reclassify to AUTO_TP
    - Disagreement         → keep NEEDS_REVIEW

Uses two independent Groq calls with slight prompt variation to simulate
inter-rater agreement (mirrors the second_opinion engine's approach).

Output:
    TESTS/evaluation/results/ai_triage_verdicts.json   per-finding AI decisions
    Updates precision_triage.json in-place
    Re-runs precision calculation → updates precision_summary.json
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TRIAGE_FILE = ROOT / "TESTS/evaluation/results/precision_triage.json"
FINDINGS_DIR = ROOT / "TESTS/evaluation/results/precision_findings"
SUMMARY_FILE = ROOT / "TESTS/evaluation/results/precision_summary.json"
AI_VERDICTS_FILE = ROOT / "TESTS/evaluation/results/ai_triage_verdicts.json"

SECURITY_CATEGORY_RULES = {
    "SECURITY-001",
    "SECURITY-002",
    "SECURITY-003",
    "SECURITY-004",
    "SECURITY-005",
    "SECURITY-006",
    "SECURITY-007",
    "SECURITY-008",
    "SECURITY-009",
    "SECURITY-010",
    "SECURITY-021",
    "SECURITY-022",
    "SECURITY-023",
    "SECURITY-024",
    "SECURITY-025",
    "SECURITY-026",
    "SECURITY-046",
    "SECRET-001",
    "SECRET-002",
    "SECRET-003",
    "SQLI-001",
    "SQLI-002",
    "SHELL-001",
    "SHELL-002",
    "XML-001",
    "YAML-001",
    "CRYPTO-001",
    "CRYPTO-002",
}

_VERDICT_RE = re.compile(r"\b(TP|FP|NEEDS_REVIEW)\b", re.IGNORECASE)

PROMPT_A = """\
You are a senior security engineer reviewing a static-analysis finding on a \
production open-source library (NOT a web application, NOT user-facing code).

Finding:
  Rule:     {rule}
  File:     {file}:{line}
  Message:  {message}
  Severity: HIGH

Code context:
```
{snippet}
```

Is this finding a genuine security vulnerability (TP) or a false positive (FP)?
Consider: is this code actually reachable by untrusted user input in typical usage?

Reply with exactly one token on line 1: TP, FP, or NEEDS_REVIEW
Then one short reason (≤ 25 words). Do not fabricate CVE numbers."""

PROMPT_B = """\
Static analysis finding in a mature, widely-used open-source library:

Rule: {rule} | Severity: HIGH
Location: {file} line {line}
Tool message: "{message}"

Relevant code:
```
{snippet}
```

In the context of this library (not a web app), classify as TP (real exploitable issue), \
FP (tool over-fires on safe code), or NEEDS_REVIEW (genuinely ambiguous).

Output format — first line: TP, FP, or NEEDS_REVIEW. Second line: brief reason."""


def _groq_call(prompt: str, api_key: str, model: str = "llama-3.3-70b-versatile") -> str:
    import httpx

    resp = httpx.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 120,
            "temperature": 0.1,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def _parse_verdict(text: str) -> tuple[str, str]:
    m = _VERDICT_RE.search(text)
    verdict = m.group(1).upper() if m else "NEEDS_REVIEW"
    reason = " ".join(ln.strip() for ln in text.splitlines() if ln.strip() and not _VERDICT_RE.fullmatch(ln.strip()))[
        :200
    ]
    return verdict, reason


def _get_snippet(repo: str, file_path: str, line: int) -> str:
    findings_path = FINDINGS_DIR / f"{repo}_findings.json"
    if not findings_path.exists():
        return "(snippet not available)"
    findings = json.loads(findings_path.read_text())
    for f in findings:
        fp = f.get("file_path") or f.get("file") or ""
        ln = f.get("line_number") or f.get("line") or 0
        if file_path in fp and abs(int(ln or 0) - line) <= 2:
            ev = f.get("evidence") or {}
            snippet = ev.get("snippet") or f.get("code_snippet") or ""
            if snippet:
                return snippet[:800]
    return "(snippet not available)"


def run_ai_triage() -> None:
    api_key = os.getenv("GROQ_API_KEY_1") or os.getenv("GROQ_API_KEY")
    if not api_key:
        print("ERROR: GROQ_API_KEY_1 not set", file=sys.stderr)
        sys.exit(1)

    triage = json.loads(TRIAGE_FILE.read_text())

    # Select security-tier HIGH NEEDS_REVIEW findings
    candidates = [
        t
        for t in triage
        if t["triage"]["verdict"] == "NEEDS_REVIEW" and t["severity"] == "high" and t["rule"] in SECURITY_CATEGORY_RULES
    ]
    print(f"AI triage targets: {len(candidates)} security-tier HIGH NEEDS_REVIEW findings")

    results = []
    promoted_tp = 0
    promoted_fp = 0

    for i, finding in enumerate(candidates, 1):
        repo = finding["repo"]
        file_path = finding["file"]
        line = finding.get("line", 0)
        rule = finding["rule"]
        message = finding["message"]

        print(f"\n[{i}/{len(candidates)}] {rule} | {repo} | {file_path.split('/')[-1]}:{line}")

        snippet = _get_snippet(repo, file_path, line)

        fmt = dict(rule=rule, file=file_path.split("/")[-1], line=line, message=message[:300], snippet=snippet)

        try:
            raw_a = _groq_call(PROMPT_A.format(**fmt), api_key)
            v_a, r_a = _parse_verdict(raw_a)
            print(f"  Call A: {v_a} — {r_a[:60]}")
            time.sleep(0.6)

            raw_b = _groq_call(PROMPT_B.format(**fmt), api_key)
            v_b, r_b = _parse_verdict(raw_b)
            print(f"  Call B: {v_b} — {r_b[:60]}")

        except Exception as e:
            print(f"  [error] {e} — keeping NEEDS_REVIEW")
            results.append(
                {
                    "rule": rule,
                    "repo": repo,
                    "file": file_path,
                    "line": line,
                    "v_a": "ERROR",
                    "v_b": "ERROR",
                    "final": "NEEDS_REVIEW",
                    "reason": str(e),
                }
            )
            continue

        # Consensus rule: both must agree to reclassify
        if v_a == v_b == "FP":
            final = "AUTO_FP"
            reason = f"[AI triage] both calls agree FP. A: {r_a[:80]}. B: {r_b[:80]}"
            promoted_fp += 1
        elif v_a == v_b == "TP":
            final = "AUTO_TP"
            reason = f"[AI triage] both calls agree TP. A: {r_a[:80]}. B: {r_b[:80]}"
            promoted_tp += 1
        else:
            final = "NEEDS_REVIEW"
            reason = f"[AI triage] disagreement (A={v_a}, B={v_b}) — kept NR. A: {r_a[:60]}"

        print(f"  → {final}")

        results.append(
            {
                "rule": rule,
                "repo": repo,
                "file": file_path,
                "line": line,
                "v_a": v_a,
                "r_a": r_a,
                "v_b": v_b,
                "r_b": r_b,
                "final": final,
                "reason": reason,
            }
        )

        # Update triage in place
        for t in triage:
            if (
                t["repo"] == repo
                and t["file"] == file_path
                and t.get("line", 0) == line
                and t["rule"] == rule
                and t["triage"]["verdict"] == "NEEDS_REVIEW"
            ):
                if final != "NEEDS_REVIEW":
                    t["triage"] = {"verdict": final, "reason": reason}
                break

        time.sleep(0.8)

    # Write AI verdicts log
    AI_VERDICTS_FILE.write_text(
        json.dumps(
            {
                "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "method": "Two independent Groq llama-3.3-70b calls; reclassify only on unanimous agreement",
                "n_candidates": len(candidates),
                "promoted_to_auto_tp": promoted_tp,
                "promoted_to_auto_fp": promoted_fp,
                "kept_needs_review": len(candidates) - promoted_tp - promoted_fp,
                "verdicts": results,
            },
            indent=2,
        )
    )
    print(f"\n[✓] AI verdicts → {AI_VERDICTS_FILE}")

    # Write updated triage
    TRIAGE_FILE.write_text(json.dumps(triage, indent=2))
    print(f"[✓] Updated triage → {TRIAGE_FILE}")

    # Recompute precision
    _recompute_precision(triage, promoted_tp, promoted_fp)

    print(
        f"\nSummary: {promoted_tp} → AUTO_TP | {promoted_fp} → AUTO_FP | "
        f"{len(candidates) - promoted_tp - promoted_fp} kept NR"
    )


def _recompute_precision(triage: list[dict], promoted_tp: int, promoted_fp: int) -> None:
    # Pull updated numbers from the triage (levers 1+2+3 applied)
    sec_rules = SECURITY_CATEGORY_RULES
    sec_high = [
        t for t in triage if t["severity"] == "high" and t["rule"] in sec_rules and t["triage"]["verdict"] != "SKIP"
    ]
    tp = sum(1 for t in sec_high if t["triage"]["verdict"] == "AUTO_TP")
    fp = sum(1 for t in sec_high if t["triage"]["verdict"] == "AUTO_FP")
    nr = sum(1 for t in sec_high if t["triage"]["verdict"] == "NEEDS_REVIEW")
    total = len(sec_high)

    conservative = tp / total if total else 0
    optimistic = (tp + nr) / total if total else 0

    print(f"\nSecurity-tier after AI triage: {total} total, {tp} TP, {fp} FP, {nr} NR")
    print(f"  Conservative: {conservative:.1%}  (was 24.7%)")
    print(f"  Optimistic:   {optimistic:.1%}  (was 37.9% pre-L1, 29.2% post-L1+L2)")

    # Update precision_summary.json
    summary = json.loads(SUMMARY_FILE.read_text())
    summary["security_tier_conservative"]["precision"] = round(conservative, 6)
    summary["security_tier_conservative"]["tp"] = tp
    summary["security_tier_conservative"]["fp"] = fp
    summary["security_tier_conservative"]["needs_review"] = nr
    summary["security_tier_optimistic"]["precision"] = round(optimistic, 6)
    summary["security_tier_optimistic"]["tp"] = tp + nr
    summary["security_tier_optimistic"]["fp"] = fp
    summary["security_tier_optimistic"]["needs_review"] = nr
    summary["security_tier_denominator"] = total
    summary["note"] = (
        summary.get("note", "") + f" T4 Precision Enhancement (2026-05-30): L1 heuristics (SECURITY-005 regex tokens, "
        f"SECURITY-046 literal-URL/ALL_CAPS, extended subprocess paths), L2 corroboration, "
        f"L3 AI triage (2 Groq calls, unanimous consensus). {promoted_tp} NR→TP, {promoted_fp} NR→FP."
    )
    SUMMARY_FILE.write_text(json.dumps(summary, indent=2))
    print("[✓] Updated precision_summary.json")


if __name__ == "__main__":
    run_ai_triage()
