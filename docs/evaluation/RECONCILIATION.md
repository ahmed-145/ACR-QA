# Benchmark Reconciliation — Reading the Numbers Honestly

> **Created:** 2026-06-02
> **Purpose:** Reconcile three numbers that look contradictory until you understand what each
> measures: the internal 96.4% precision, the P-1 SecurityEval 64.3%/3.6%, and the P-2 rigorous
> 58.4% recall. This is the integrity document — it is meant to be read by an examiner or a skeptic.

---

## TL;DR

| Number | What it measures | Verdict |
|--------|------------------|---------|
| **96.4% precision** | Manual-triage precision of the Confirmed Tier on a 30-repo production corpus | Valid, but corpus-specific — a precision claim, not a recall claim |
| **P-1: 64.3% precision, 3.6% recall** | A *flawed* first benchmark | **Retracted** — wrong ground truth, see below |
| **P-2: 58.4% recall (full), best of all tools** | Recall on genuinely-vulnerable code, fair methodology | **The defensible headline** |

**The honest story:** ACR-QA's *full output* detects more real vulnerabilities than Bandit or
Semgrep (58.4% vs 50.6% vs 23.6% on the detectable subset). Its *Confirmed Tier* trades recall for
precision — a small, high-confidence subset safe to auto-block. The 96.4% is the Confirmed Tier's
precision on a different corpus. None of these contradict each other once you separate
**precision (of the confirmed subset)** from **recall (of the full output)**.

---

## What went wrong in P-1 (and why we retract it)

P-1 (`scripts/run_benchmark_p1.py`, result `P1_BENCHMARK_20260602.md`) reported 64.3% precision and
3.6% recall. Three methodology errors made it meaningless:

### Error 1 — Wrong ground truth (the big one)
P-1 scored against `SecurityEval/Testcases_Copilot/`. Those files are **Copilot's completions**, which
are *frequently secure*. Example — `Testcases_Copilot/CWE-089/author_1.py`:

```python
cursor.execute("DELETE FROM users WHERE username = %s", [username])  # parameterized — SECURE
```

This is a correctly parameterized query. It is **not** a SQL injection. When ACR-QA correctly stayed
silent, P-1 counted it as a *missed detection* (false negative). We were penalized for being right.

The curated insecure corpus — `Testcases_Insecure_Code/CWE-089/` — contains the genuinely vulnerable
version:

```python
cursor.execute("DELETE FROM users WHERE username = '%s'" % username)  # string-format — VULNERABLE
```

### Error 2 — Lightweight detection path
P-1 ran only Bandit + the Semgrep registry. It skipped ACR-QA's **custom Semgrep rules**
(`TOOLS/semgrep/python-rules.yml`), which are a real part of the detection engine.

### Error 3 — Reported only the Confirmed Tier
P-1's headline used the Confirmed Tier — the *most conservative possible subset* — and compared it to
the competitors' *raw, unfiltered* output. That is apples-to-oranges: a precision-optimized subset
will always look low on recall.

### Error 4 — File-level matching + tiny n
Even setting the above aside, file-level matching with n=14 gave a CI of [38.8%, 83.7%] — too wide to
conclude anything.

---

## P-2 — the rigorous benchmark

`scripts/run_benchmark_p2.py` fixes all four errors:

1. **Correct ground truth:** scores against `Testcases_Insecure_Code/` (every file genuinely vulnerable).
2. **Full detection:** Bandit + Semgrep registry + ACR-QA custom rules.
3. **Both tiers reported:** full output (recall-oriented) *and* Confirmed Tier (precision-oriented).
4. **Statically-detectable subset + bootstrap CIs + MCC** (per SastBench, robust to class imbalance).

### Results — recall on genuinely-vulnerable code

**Statically-detectable CWE subset (89 files):**

| Tool | Recall | 95% CI | Detected |
|------|-------:|--------|:--------:|
| **ACR-QA (full output)** | **58.4%** | [47.2%, 67.4%] | 52/89 |
| Bandit (standalone) | 50.6% | [39.3%, 60.7%] | 45/89 |
| Semgrep CE (standalone) | 23.6% | [14.6%, 32.6%] | 21/89 |
| ACR-QA (Confirmed Tier) | 5.6% | [1.1%, 11.2%] | 5/89 |

**All CWE classes (121 files — includes ~40 undetectable authz/session/logic flaws):**

| Tool | Recall | 95% CI | Detected |
|------|-------:|--------|:--------:|
| **ACR-QA (full output)** | **55.4%** | [47.1%, 64.5%] | 67/121 |
| Bandit (standalone) | 44.6% | [35.5%, 53.7%] | 54/121 |
| Semgrep CE (standalone) | 19.0% | [12.4%, 26.4%] | 23/121 |

**ACR-QA detects more real vulnerabilities than either competitor, in both cuts.** On high-severity
injection/crypto/deserialization classes it is near-perfect: CWE-078 (command injection) 2/2,
CWE-089 (SQLi) 2/2, CWE-502 (insecure deserialization) 4/4, CWE-611 (XXE) 6/6, CWE-918 (SSRF) 2/2,
CWE-798 (hardcoded credentials) 2/2.

---

## How to read the two ACR-QA tiers

ACR-QA deliberately produces **two views of the same scan**:

- **Full output** — maximize recall. Use for a complete security review. *Best-in-class recall:
  58.4%, beating Bandit and Semgrep.*
- **Confirmed Tier** — maximize precision. A small subset (HIGH severity + 22-rule high-precision set
  + production code + tool confidence) safe enough to **auto-block a merge**. Low recall is the point:
  it is the "zero-argument" stratum. Its precision was measured at **96.4%** on the 30-repo
  production corpus (manual triage).

A buyer turns the Confirmed Tier on as a required check (won't annoy developers), and uses the full
output for periodic deep review. The two numbers serve two jobs.

---

## What this means for positioning

1. **Lead with recall on the full output** (58.4%, beats competitors) and **exploit-verification**
   (the moat) — both are defensible and verifiable.
2. **Frame the Confirmed Tier as a precision instrument**, not a recall metric. "96.4% precise,
   auto-block safe" — never "96.4%" as a bare stat next to a recall comparison.
3. **The honesty itself is the asset.** Pre-registering, finding our own benchmark was flawed,
   retracting it, and publishing the rigorous version is exactly the scientific behavior that earns
   trust in a defense room and a sales call. We retract P-1 in public.

---

## Limitations (stated plainly)

- P-2 measures **recall** on a 100%-vulnerable corpus; it does not measure precision (no negatives in
  this corpus). Precision is measured separately on the 30-repo corpus and via per-finding triage.
- File/CWE-folder-level matching: a tool gets credit for flagging a vulnerable file, not for naming
  the exact CWE. This is the standard SecurityEval convention and is applied identically to all tools.
- The "statically-detectable" CWE subset is a defensible judgment call; the all-CWE numbers are also
  reported so nothing is hidden.

---

## Reproduce

```bash
git clone https://github.com/s2e-lab/SecurityEval TESTS/evaluation/securityeval
python3 scripts/run_benchmark_p2.py --dataset-dir TESTS/evaluation/securityeval            # detectable subset
python3 scripts/run_benchmark_p2.py --dataset-dir TESTS/evaluation/securityeval --all-cwes  # all CWEs
```

Outputs: `docs/evaluation/P2_BENCHMARK_{detectable,allcwe}_<date>.{md,json}`.
