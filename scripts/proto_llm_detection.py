#!/usr/bin/env python3
"""
PROTOTYPE — does LLM-augmented detection lift RealVuln recall, and at what FPR?

Phase 0 of docs/GO_BIG_LLM_DETECTION_PLAN.md. Decoupled from Docker: RealVuln scoring
is static ground-truth matching (file + CWE-family + line +/-10), so to measure whether
the LLM *finds more*, we score LLM candidates against GT directly. FPR on the 120 FP-trap
entries + non-GT hits tells us how much exploit-gating we'll need.

Reports per repo + aggregate: rule-based recall vs LLM recall vs UNION recall, and FPR.

Usage:
    python3 scripts/proto_llm_detection.py --repos realvuln-vampi realvuln-dsvpwa realvuln-flask-xss
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))

_RV = _ROOT / "TESTS" / "evaluation" / "realvuln"
_GT = _RV / "ground-truth"
_REPOS = _RV / "repos"
LINE_TOL = 10
MAX_FILE_CHARS = 12000  # keep prompts within token budget


# ---------- LLM client (reuse Groq keys from .env) ----------
def _load_keys() -> list[str]:
    env = _ROOT / ".env"
    keys: list[str] = []
    if env.exists():
        for line in env.read_text().splitlines():
            m = re.match(r"\s*(GROQ_API_KEY_\d+)\s*=\s*(.+)", line)
            if m:
                keys.append(m.group(2).strip().strip('"').strip("'"))
    keys = [k for k in keys if k and "your" not in k.lower()]
    return keys


_KEYS = _load_keys()
_MODEL = "llama-3.3-70b-versatile"
_key_idx = 0
_CACHE = _ROOT / "DATA" / "proto_llm_cache"
_CACHE.mkdir(parents=True, exist_ok=True)


# ---------- CWE-family normalization (use RealVuln's own families) ----------
def _load_cwe_family_map() -> dict[str, str]:
    fam_file = _RV / "config" / "cwe-families.json"
    out: dict[str, str] = {}
    if fam_file.exists():
        d = json.loads(fam_file.read_text())
        for fam, info in d.get("families", {}).items():
            for cwe in info.get("cwes", []):
                out[cwe.upper()] = fam
    return out


_CWE_FAM = _load_cwe_family_map()


def _fam(cwe: str) -> str | None:
    return _CWE_FAM.get(cwe.upper())


DETECT_PROMPT = """You are a security code auditor. Analyze the following Python file for \
SECURITY VULNERABILITIES ONLY (injection, XSS, command injection, SSRF, path traversal, \
insecure deserialization, SSTI, hardcoded secrets, weak crypto, open redirect).

Return ONLY a JSON array, no prose. Each item:
{{"line": <int line number of the vulnerable code>, "cwe": "CWE-XX", "why": "<short>"}}

If no vulnerabilities, return []. Be precise on the line number. Focus on real, exploitable \
flaws a developer must fix — not style. File: {fname}

```python
{code}
```"""


def _extract_json_array(txt: str) -> list:
    """Find the last valid JSON array of objects in text (robust to reasoning prefixes)."""
    best: list = []
    for m in re.finditer(r"\[(?:[^\[\]]|\[[^\[\]]*\])*\]", txt, re.DOTALL):
        try:
            arr = json.loads(m.group(0))
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(arr, list) and (not arr or isinstance(arr[0], dict)):
            best = arr  # keep the last well-formed array (usually the final answer)
    return best


def _llm_detect_file(fname: str, code: str) -> list[dict]:
    global _key_idx
    if not _KEYS:
        raise RuntimeError("No GROQ_API_KEY_* found in .env")
    from groq import Groq

    key = _KEYS[_key_idx % len(_KEYS)]
    _key_idx += 1
    client = Groq(api_key=key)
    prompt = DETECT_PROMPT.format(fname=fname, code=code[:MAX_FILE_CHARS])
    for attempt in range(3):
        try:
            comp = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=_MODEL,
                temperature=0.0,
                max_tokens=1200,
            )
            msg = comp.choices[0].message
            # reasoning models (gpt-oss, qwen3) may put the answer in .reasoning, not .content
            txt = (msg.content or "") + "\n" + (getattr(msg, "reasoning", None) or "")
            items = _extract_json_array(txt)
            out = []
            for it in items:
                if isinstance(it, dict) and "line" in it and "cwe" in it:
                    try:
                        out.append({"file": fname, "line": int(it["line"]), "cwe": str(it["cwe"]).upper().strip()})
                    except (ValueError, TypeError):
                        continue
            return out
        except Exception as e:  # noqa: BLE001
            if "rate" in str(e).lower() or "429" in str(e):
                time.sleep(3 * (attempt + 1))
                continue
            if attempt == 2:
                print(f"    ! LLM error on {fname}: {str(e)[:120]}")
            time.sleep(1)
    return []


# ---------- ground truth ----------
def _load_gt(repo: str) -> list[dict]:
    f = _GT / repo / "ground-truth.json"
    if not f.exists():
        # some dirs nest one level
        cand = list((_GT / repo).glob("**/ground-truth.json"))
        if not cand:
            return []
        f = cand[0]
    d = json.loads(f.read_text())
    entries = d if isinstance(d, list) else d.get("findings", d.get("entries", []))
    if isinstance(entries, dict):
        entries = list(entries.values())
    return [e for e in entries if isinstance(e, dict)]


def _repo_src(repo: str) -> Path:
    return _REPOS / repo


def _gt_lines(e: dict) -> tuple[int | None, int | None]:
    loc = e.get("location", {})
    return loc.get("start_line"), loc.get("end_line")


def _matches(cand: dict, e: dict) -> bool:
    if cand["cwe"] not in e.get("acceptable_cwes", []):
        return False
    if cand["file"] != e.get("file"):
        return False
    s, en = _gt_lines(e)
    if s is None:
        return True
    lo, hi = s - LINE_TOL, (en or s) + LINE_TOL
    return lo <= cand["line"] <= hi


# ---------- scoring ----------
def score_repo(repo: str) -> dict:
    gt = _load_gt(repo)
    tp_entries = [e for e in gt if e.get("is_vulnerable", True)]
    fp_entries = [e for e in gt if e.get("is_vulnerable") is False]
    src = _repo_src(repo)
    if not src.exists() or not tp_entries:
        return {"repo": repo, "skip": True}

    # gather LLM candidates across all python files (cached per-model — iterate scoring for free)
    _safe = _MODEL.replace("/", "_")
    cache_f = _CACHE / f"{repo}__{_safe}.json"
    if cache_f.exists():
        cands = json.loads(cache_f.read_text())
        print("    (using cached candidates)")
    else:
        cands = []
        pyfiles = sorted(src.rglob("*.py"))
        for pf in pyfiles:
            rel = str(pf.relative_to(src))
            try:
                code = pf.read_text(errors="replace")
            except Exception:  # noqa: BLE001
                continue
            if not code.strip():
                continue
            cands.extend(_llm_detect_file(rel, code))
        cache_f.write_text(json.dumps(cands))

    # recall at three strictness levels (diagnose: missing vs mislocalizing)
    def _file_line(c, e):  # ignore CWE
        if c["file"] != e.get("file"):
            return False
        s, en = _gt_lines(e)
        if s is None:
            return True
        return (s - LINE_TOL) <= c["line"] <= ((en or s) + LINE_TOL)

    def _file_only(c, e):
        return c["file"] == e.get("file")

    def _fam_match(c, e):  # CWE-NORMALIZED: same family + file + line±tol
        if c["file"] != e.get("file"):
            return False
        cf = _fam(c["cwe"])
        if cf is None or cf not in {_fam(x) for x in e.get("acceptable_cwes", [])}:
            return False
        s, en = _gt_lines(e)
        if s is None:
            return True
        return (s - LINE_TOL) <= c["line"] <= ((en or s) + LINE_TOL)

    # rule-based findings (Bandit+Semgrep+custom) on the SAME repo → union test
    try:
        from scripts.run_realvuln_benchmark import run_acrqa_full

        rule_f = run_acrqa_full(str(src))
    except Exception as exc:  # noqa: BLE001
        print(f"    ! rule-based run failed: {str(exc)[:90]}")
        rule_f = []
    union = cands + rule_f
    rec_rules = sum(1 for e in tp_entries if any(_matches(c, e) for c in rule_f)) / len(tp_entries)
    rec_union = sum(1 for e in tp_entries if any(_matches(c, e) for c in union)) / len(tp_entries)

    matched = sum(1 for e in tp_entries if any(_matches(c, e) for c in cands))
    matched_fam = sum(1 for e in tp_entries if any(_fam_match(c, e) for c in cands))
    matched_fl = sum(1 for e in tp_entries if any(_file_line(c, e) for c in cands))
    matched_fo = sum(1 for e in tp_entries if any(_file_only(c, e) for c in cands))
    recall = matched / len(tp_entries) if tp_entries else 0.0

    # FPR proxy: candidates that hit an FP-trap location, or hit no TP entry at all
    fp_hits = 0
    for c in cands:
        if any(_matches(c, e) for e in tp_entries):
            continue  # a real TP, not a false alarm
        # did it land on a known FP trap, or just nowhere true?
        fp_hits += 1
    # FPR-ish: false alarms / (false alarms + true detections), bounded
    fpr = fp_hits / (fp_hits + matched) if (fp_hits + matched) else 0.0

    return {
        "repo": repo,
        "tp_entries": len(tp_entries),
        "fp_traps": len(fp_entries),
        "llm_candidates": len(cands),
        "matched": matched,
        "llm_recall": round(recall, 3),
        "recall_rules": round(rec_rules, 3),
        "recall_union": round(rec_union, 3),
        "union_lift": round(rec_union - rec_rules, 3),
        "recall_cwe_family": round(matched_fam / len(tp_entries), 3) if tp_entries else 0,
        "recall_file_line": round(matched_fl / len(tp_entries), 3) if tp_entries else 0,
        "recall_file_only": round(matched_fo / len(tp_entries), 3) if tp_entries else 0,
        "false_alarms": fp_hits,
        "llm_fpr_proxy": round(fpr, 3),
    }


def main() -> None:
    global _MODEL
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos", nargs="+", default=["realvuln-vampi", "realvuln-dsvpwa", "realvuln-flask-xss"])
    ap.add_argument("--model", default=_MODEL, help="Groq model id (e.g. openai/gpt-oss-120b)")
    args = ap.parse_args()
    _MODEL = args.model

    print(f"LLM-detection prototype — model={_MODEL}, keys={len(_KEYS)}, line_tol=±{LINE_TOL}")
    print("=" * 72)
    rows = []
    for repo in args.repos:
        print(f"[{repo}] scanning...")
        r = score_repo(repo)
        if r.get("skip"):
            print("  skipped (no source/GT)")
            continue
        rows.append(r)
        print(
            f"  TP={r['tp_entries']:3}  RULES={r['recall_rules']:.0%}  LLM={r['llm_recall']:.0%}  "
            f"UNION={r['recall_union']:.0%} (lift {r['union_lift']:+.0%})  "
            f"llm-file+line={r['recall_file_line']:.0%} fpr~={r['llm_fpr_proxy']:.0%}"
        )

    if rows:
        tot_tp = sum(r["tp_entries"] for r in rows)
        tot_m = sum(r["matched"] for r in rows)
        tot_r = sum(round(r["recall_rules"] * r["tp_entries"]) for r in rows)
        tot_u = sum(round(r["recall_union"] * r["tp_entries"]) for r in rows)
        agg_recall = tot_m / tot_tp if tot_tp else 0
        agg_rules = tot_r / tot_tp if tot_tp else 0
        agg_union = tot_u / tot_tp if tot_tp else 0
        print("=" * 72)
        print(
            f"AGGREGATE  RULES={agg_rules:.1%}  LLM-alone={agg_recall:.1%}  "
            f"UNION={agg_union:.1%}  (union lift {agg_union - agg_rules:+.1%})"
        )
        print("DECISION: union lift > ~+8pp = real fast win. ≈0 = LLM adds only noise → future work.")
        print("\nCompare vs RealVuln rule-based baseline (full: 25.1%, detectable: 37.8%).")
        out = _ROOT / "docs" / "evaluation" / "PROTO_LLM_DETECTION.json"
        out.write_text(
            json.dumps(
                {
                    "rows": rows,
                    "agg_rules": agg_rules,
                    "agg_llm": agg_recall,
                    "agg_union": agg_union,
                    "union_lift": agg_union - agg_rules,
                },
                indent=2,
            )
        )
        print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
