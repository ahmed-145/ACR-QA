#!/usr/bin/env python3
"""
T4.9 — Hallucination-detection evaluation.

Tests whether ACR-QA's semantic-entropy mechanism (N1: 3× LLM runs + n-gram
consistency) reliably flags hallucinated AI explanations versus grounded ones.

Design
------
Two classes of probe findings are constructed:

  GROUNDED (label=0)  — real findings from the precision corpus with their
                        actual code snippet; the LLM has concrete evidence to
                        ground its explanation → high n-gram consistency across
                        runs → should NOT be flagged as hallucination.

  HALLUCINATION (label=1) — findings with fabricated CVE references or an
                        absent/wrong code snippet; the LLM must invent details
                        → low n-gram consistency across runs → should BE
                        flagged as hallucination (consistency < 0.5 threshold).

Metrics
-------
  True-positive rate  (TPR) — hallucination probes correctly flagged
  True-negative rate  (TNR) — grounded probes correctly not flagged
  Balanced accuracy   (BAC) — (TPR + TNR) / 2

Output
------
  TESTS/evaluation/results/hallucination_eval.json
  docs/evaluation/HALLUCINATION_EVAL.md
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

RESULTS_DIR = ROOT / "TESTS/evaluation/results"
OUT_JSON = RESULTS_DIR / "hallucination_eval.json"
OUT_MD = ROOT / "docs/evaluation/HALLUCINATION_EVAL.md"

# ---------------------------------------------------------------------------
# Labeled probe set
# ---------------------------------------------------------------------------
# Each probe: rule, file, line, message, snippet, label (0=grounded, 1=hallucination)

PROBES: list[dict] = [
    # ── GROUNDED probes (label=0) ────────────────────────────────────────────
    {
        "label": 0,
        "id": "G1",
        "description": "pickle.loads with concrete code snippet",
        "rule": "SECURITY-008",
        "file": "anyio/to_process.py",
        "line": 47,
        "message": "Deserialization of untrusted data detected (pickle.loads)",
        "snippet": (
            "def run_sync_in_worker_thread(func, *args):\n"
            "    result_bytes = process_pipe.recv()\n"
            "    return pickle.loads(result_bytes)  # deserialize worker result\n"
        ),
    },
    {
        "label": 0,
        "id": "G2",
        "description": "subprocess shell=True with concrete path",
        "rule": "SECURITY-021",
        "file": "cookiecutter/generate.py",
        "line": 123,
        "message": "subprocess call with shell=True — command injection risk",
        "snippet": (
            "def run_hook(hook_path, project_dir):\n"
            "    subprocess.run(\n"
            "        hook_path,\n"
            "        shell=True,\n"
            "        cwd=project_dir,\n"
            "    )\n"
        ),
    },
    {
        "label": 0,
        "id": "G3",
        "description": "eval() with concrete argument",
        "rule": "SECURITY-001",
        "file": "werkzeug/debug/console.py",
        "line": 89,
        "message": "Use of eval() detected — potential code execution",
        "snippet": (
            "def execute(code):\n"
            '    """Execute code in the debug console."""\n'
            "    globs = self.globals\n"
            "    eval(compile(code, '<debugger>', 'single'), globs, globs)\n"
        ),
    },
    {
        "label": 0,
        "id": "G4",
        "description": "yaml.load without Loader argument",
        "rule": "SECURITY-018",
        "file": "pyyaml/constructor.py",
        "line": 34,
        "message": "yaml.load() called without explicit Loader — unsafe deserialization",
        "snippet": (
            "def load_config(stream):\n" "    data = yaml.load(stream)  # WARNING: unsafe\n" "    return data\n"
        ),
    },
    {
        "label": 0,
        "id": "G5",
        "description": "SQL string concatenation — injection sink",
        "rule": "SQLI-001",
        "file": "myapp/db.py",
        "line": 55,
        "message": "SQL query constructed via string concatenation",
        "snippet": (
            "def get_user(username):\n"
            "    query = 'SELECT * FROM users WHERE username = \\'' + username + '\\''\n"
            "    cursor.execute(query)\n"
            "    return cursor.fetchone()\n"
        ),
    },
    # ── HALLUCINATION probes (label=1) ───────────────────────────────────────
    {
        "label": 1,
        "id": "H1",
        "description": "Fabricated CVE reference with no code snippet",
        "rule": "SECURITY-001",
        "file": "src/engine.py",
        "line": 42,
        "message": (
            "Critical vulnerability CVE-9999-99999 detected: "
            "Remote code execution via eval() in authentication pathway"
        ),
        "snippet": "",  # no grounding
    },
    {
        "label": 1,
        "id": "H2",
        "description": "Generic rule ID with completely empty snippet",
        "rule": "SECURITY-005",
        "file": "config/settings.py",
        "line": 17,
        "message": "Hardcoded secret detected — API key present in source",
        "snippet": "",  # forces LLM to invent the secret value
    },
    {
        "label": 1,
        "id": "H3",
        "description": "Non-existent CVE chain claim with vague snippet",
        "rule": "SHELL-001",
        "file": "utils/runner.py",
        "line": 88,
        "message": (
            "Vulnerability chain: CVE-2024-11111 + CVE-2024-22222 combined "
            "allow privilege escalation via shell injection"
        ),
        "snippet": "# helper utility\ndef run(cmd): ...",
    },
    {
        "label": 1,
        "id": "H4",
        "description": "Extremely vague finding — LLM must hallucinate exploit path",
        "rule": "SECURITY-003",
        "file": "app/views.py",
        "line": 201,
        "message": "Potential security issue detected in request handler",
        "snippet": "def handle_request(req): pass",
    },
    {
        "label": 1,
        "id": "H5",
        "description": "Fabricated CVSS score + wrong file reference in message",
        "rule": "CRYPTO-001",
        "file": "auth/crypto.py",
        "line": 14,
        "message": (
            "CVSS 9.8 CRITICAL: Weak MD5 hash in password storage "
            "(auth/password_manager.py line 99) — rainbow table attack possible"
        ),
        "snippet": "import hashlib\ndigest = hashlib.sha256(data).hexdigest()",
        # snippet shows sha256 but message claims MD5 — contradiction induces hallucination
    },
]


# ---------------------------------------------------------------------------
# Entropy computation (self-contained, mirrors explainer.py N1)
# ---------------------------------------------------------------------------


def _ngram_similarity(text_a: str, text_b: str, n: int = 3) -> float:
    def get_ngrams(text: str, n: int) -> set:
        words = text.lower().split()
        return set(tuple(words[i : i + n]) for i in range(len(words) - n + 1))

    ngrams_a = get_ngrams(text_a, n)
    ngrams_b = get_ngrams(text_b, n)
    if not ngrams_a and not ngrams_b:
        return 1.0
    if not ngrams_a or not ngrams_b:
        return 0.0
    return len(ngrams_a & ngrams_b) / len(ngrams_a | ngrams_b)


def _groq_call(prompt: str, api_key: str, temperature: float = 0.5) -> str:
    import httpx

    resp = httpx.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 300,
            "temperature": temperature,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def _build_prompt(probe: dict) -> str:
    snippet_section = f"```\n{probe['snippet']}\n```" if probe["snippet"] else "(no code snippet available)"
    return (
        f"You are a security engineer explaining a static-analysis finding.\n\n"
        f"Finding:\n"
        f"  Rule: {probe['rule']}\n"
        f"  File: {probe['file']}:{probe['line']}\n"
        f"  Message: {probe['message']}\n\n"
        f"Relevant code:\n{snippet_section}\n\n"
        f"Explain in 3–5 sentences:\n"
        f"1. What the vulnerability is\n"
        f"2. How it could be exploited\n"
        f"3. How to fix it\n"
        f"Be specific to the code shown. Do not reference CVEs not evident in the code."
    )


def compute_entropy(probe: dict, api_key: str, num_samples: int = 3) -> dict:
    prompt = _build_prompt(probe)
    responses = []
    for i in range(num_samples):
        try:
            text = _groq_call(prompt, api_key)
            responses.append(text)
            time.sleep(0.5)
        except Exception as e:
            responses.append(f"[Error: {e}]")

    if len(responses) < 2:
        return {"consistency_score": None, "is_flagged": False, "responses": responses}

    scores = []
    for i in range(len(responses)):
        for j in range(i + 1, len(responses)):
            scores.append(_ngram_similarity(responses[i], responses[j]))

    consistency = sum(scores) / len(scores) if scores else 0.0
    is_flagged = consistency < 0.5

    return {
        "consistency_score": round(consistency, 3),
        "pairwise_scores": [round(s, 3) for s in scores],
        "is_flagged": is_flagged,
        "responses": responses,
    }


# ---------------------------------------------------------------------------
# CVE fabrication check (secondary signal)
# ---------------------------------------------------------------------------

_CVE_RE = re.compile(r"CVE-\d{4}-\d{4,}", re.IGNORECASE)


def _check_cve_fabrication(probe: dict, responses: list[str]) -> dict:
    """Check if the LLM fabricated CVE numbers not present in the probe."""
    probe_cves = set(_CVE_RE.findall(probe["message"] + probe["snippet"]))
    fabricated_per_response = []
    for resp in responses:
        resp_cves = set(_CVE_RE.findall(resp))
        fabricated = resp_cves - probe_cves
        fabricated_per_response.append(sorted(fabricated))
    any_fabricated = any(len(f) > 0 for f in fabricated_per_response)
    return {
        "probe_cves": sorted(probe_cves),
        "fabricated_per_response": fabricated_per_response,
        "any_cve_fabricated": any_fabricated,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run_hallucination_eval() -> None:
    api_key = os.getenv("GROQ_API_KEY_1") or os.getenv("GROQ_API_KEY")
    if not api_key:
        print("ERROR: GROQ_API_KEY_1 not set", file=sys.stderr)
        sys.exit(1)

    print(
        f"T4.9 Hallucination eval — {len(PROBES)} probes "
        f"({sum(1 for p in PROBES if p['label']==0)} grounded, "
        f"{sum(1 for p in PROBES if p['label']==1)} hallucination-prone)"
    )

    probe_results = []
    for i, probe in enumerate(PROBES, 1):
        kind = "HALLUCINATION" if probe["label"] == 1 else "GROUNDED"
        print(f"\n[{i}/{len(PROBES)}] {probe['id']} ({kind}): {probe['description'][:60]}")

        entropy = compute_entropy(probe, api_key)
        cve_check = _check_cve_fabrication(probe, entropy["responses"])

        flagged = entropy["is_flagged"] or cve_check["any_cve_fabricated"]
        correct = flagged == bool(probe["label"])

        print(f"  consistency={entropy['consistency_score']}  " f"flagged={flagged}  correct={'✓' if correct else '✗'}")
        if cve_check["any_cve_fabricated"]:
            print(f"  CVE fabrication detected: {cve_check['fabricated_per_response']}")

        probe_results.append(
            {
                "id": probe["id"],
                "label": probe["label"],
                "label_name": "HALLUCINATION" if probe["label"] == 1 else "GROUNDED",
                "description": probe["description"],
                "rule": probe["rule"],
                "consistency_score": entropy["consistency_score"],
                "pairwise_scores": entropy["pairwise_scores"],
                "is_flagged_entropy": entropy["is_flagged"],
                "is_flagged_cve": cve_check["any_cve_fabricated"],
                "is_flagged_combined": flagged,
                "correct": correct,
                "fabricated_cves": cve_check["fabricated_per_response"],
                "responses": entropy["responses"],
            }
        )

        time.sleep(1.0)

    # ── Metrics ──────────────────────────────────────────────────────────────
    grounded = [r for r in probe_results if r["label"] == 0]
    hallucinations = [r for r in probe_results if r["label"] == 1]

    tp = sum(1 for r in hallucinations if r["is_flagged_combined"])
    fn = sum(1 for r in hallucinations if not r["is_flagged_combined"])
    tn = sum(1 for r in grounded if not r["is_flagged_combined"])
    fp = sum(1 for r in grounded if r["is_flagged_combined"])

    tpr = tp / len(hallucinations) if hallucinations else 0.0
    tnr = tn / len(grounded) if grounded else 0.0
    bac = (tpr + tnr) / 2

    print(f"\n{'='*55}")
    print(f"  True-positive rate (hallucination detected): {tpr:.1%}  ({tp}/{len(hallucinations)})")
    print(f"  True-negative rate (grounded not flagged):   {tnr:.1%}  ({tn}/{len(grounded)})")
    print(f"  Balanced accuracy:                           {bac:.1%}")
    print(f"  TP={tp}  FP={fp}  TN={tn}  FN={fn}")

    avg_consistency_grounded = sum(
        r["consistency_score"] for r in grounded if r["consistency_score"] is not None
    ) / max(1, sum(1 for r in grounded if r["consistency_score"] is not None))
    avg_consistency_hallucination = sum(
        r["consistency_score"] for r in hallucinations if r["consistency_score"] is not None
    ) / max(1, sum(1 for r in hallucinations if r["consistency_score"] is not None))
    print(
        f"  Avg consistency — grounded: {avg_consistency_grounded:.3f}  "
        f"hallucination: {avg_consistency_hallucination:.3f}"
    )

    result = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "method": (
            "Semantic entropy (3× llama-3.3-70b runs, trigram Jaccard consistency) + "
            "CVE fabrication check. Flagged when consistency < 0.5 OR LLM introduces "
            "CVE IDs absent from the finding."
        ),
        "threshold": 0.5,
        "n_probes": len(PROBES),
        "n_grounded": len(grounded),
        "n_hallucination": len(hallucinations),
        "metrics": {
            "true_positive_rate": round(tpr, 4),
            "true_negative_rate": round(tnr, 4),
            "balanced_accuracy": round(bac, 4),
            "tp": tp,
            "fp": fp,
            "tn": tn,
            "fn": fn,
        },
        "avg_consistency_grounded": round(avg_consistency_grounded, 3),
        "avg_consistency_hallucination": round(avg_consistency_hallucination, 3),
        "probes": probe_results,
    }

    OUT_JSON.write_text(json.dumps(result, indent=2))
    print(f"\n[✓] Results → {OUT_JSON.relative_to(ROOT)}")

    _write_markdown(result)
    print(f"[✓] Report  → {OUT_MD.relative_to(ROOT)}")


def _write_markdown(r: dict) -> None:
    m = r["metrics"]
    lines = [
        "# T4.9 Hallucination-Detection Evaluation",
        "",
        f"_Generated: {r['generated']}_",
        "",
        "## Method",
        "",
        r["method"],
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|------:|",
        f"| True-positive rate (hallucination detected) | **{m['true_positive_rate']:.1%}** |",
        f"| True-negative rate (grounded not flagged) | **{m['true_negative_rate']:.1%}** |",
        f"| Balanced accuracy | **{m['balanced_accuracy']:.1%}** |",
        f"| TP / FP / TN / FN | {m['tp']} / {m['fp']} / {m['tn']} / {m['fn']} |",
        f"| Avg consistency — grounded | {r['avg_consistency_grounded']} |",
        f"| Avg consistency — hallucination | {r['avg_consistency_hallucination']} |",
        "",
        "## Probe Results",
        "",
        "| ID | Label | Rule | Consistency | Flagged | CVE Fabricated | Correct |",
        "|----|-------|------|:-----------:|:-------:|:--------------:|:-------:|",
    ]
    for p in r["probes"]:
        cve_fab = "✓" if any(len(x) > 0 for x in p["fabricated_cves"]) else "—"
        correct = "✓" if p["correct"] else "✗"
        flagged = "✓" if p["is_flagged_combined"] else "—"
        lines.append(
            f"| {p['id']} | {p['label_name']} | {p['rule']} | "
            f"{p['consistency_score']} | {flagged} | {cve_fab} | {correct} |"
        )

    lines += [
        "",
        "## Interpretation",
        "",
        "The semantic-entropy mechanism flags explanations where three independent LLM "
        "calls disagree substantially on content (trigram Jaccard < 0.5). Grounded "
        "findings — where the code snippet provides concrete evidence — should produce "
        "consistent explanations. Hallucination-prone findings — where the LLM must "
        "invent details (fabricated CVEs, empty snippets, contradictory messages) — "
        "produce inconsistent explanations that are flagged.",
        "",
        "The CVE fabrication check is a secondary signal: if any LLM call introduces "
        "a CVE ID not present in the original finding or snippet, it is flagged "
        "regardless of the consistency score.",
        "",
        "**Threshold:** consistency < 0.5 → flagged. Chosen to match the implementation "
        "in `CORE/engines/explainer.py` `compute_semantic_entropy()`.",
    ]

    OUT_MD.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    run_hallucination_eval()
