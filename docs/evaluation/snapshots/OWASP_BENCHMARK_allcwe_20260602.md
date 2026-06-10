# ACR-QA OWASP-Methodology Python Benchmark

> **Generated:** 2026-06-02T23:55:22.137479+00:00
> **ACR-QA version:** 5.0.0rc1
> **Corpus:** SecurityEval (Insecure_Code = TPs, Copilot = TNs)
> **Scope:** All CWE classes
> **Methodology:** OWASP Benchmark scoring (TPR, FPR, Youden J, MCC)
> **Bootstrap CIs:** 2,000 resamples, 95% confidence

## Overview

This benchmark follows the **OWASP Benchmark Project** methodology:
- Every file in `Testcases_Insecure_Code/` is a labeled **True Positive** (vulnerable)
- Every file in `Testcases_Copilot/` is a labeled **True Negative** (secure completion)
- A tool is scored on **both**: catching real vulns (TPR) AND staying silent on safe code (FPR)
- Primary metric: **Youden J = TPR − FPR** (>0 = better than random, >0.4 = strong)

## Results

| Tool | TPR (recall) | FPR | Youden J | MCC | Precision | F1 |
|------|:---:|:---:|:---:|:---:|:---:|:---:|
| **ACR-QA (full output)** | **80.2%** [72.7%, 86.8%] | 65.4% | **0.148** [4.2%, 25.8%] | 0.165 | 53.3% | 64.0% |
| Bandit (standalone) | 44.6% [35.5%, 53.7%] | 33.8% | 0.108 [-1.4%, 23.5%] | 0.110 | 55.1% | 49.3% |
| Semgrep CE (standalone) | 19.0% [12.4%, 26.4%] | 14.6% | 0.044 [-5.2%, 13.6%] | 0.059 | 54.8% | 28.2% |
| ACR-QA (Confirmed Tier) | 0.0% [0.0%, 0.0%] | 0.0% | 0.000 [0.0%, 0.0%] | 0.000 | 0.0% | 0.0% |

**Industry baselines (Java OWASP Benchmark 2024 — different language, context only):**

| Tool | TPR | FPR | Youden J |
|------|:---:|:---:|:---:|
| SonarQube | 50% | 35% | 0.15 |
| Checkmarx | 62% | 51% | 0.11 |
| FindBugs/SpotBugs | 52% | 6% | 0.46 |

## Sample sizes

- **TP corpus** (Insecure_Code): 121 files
- **TN corpus** (Copilot): 130 files
- **Total**: 251 labeled files

## Per-CWE Results (ACR-QA full output)

| CWE | TPR | FPR | Youden J | TP | FN | FP | TN |
|-----|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| CWE-020 ❌ | 100% | 100% | 0.00 | 6 | 0 | 6 | 0 |
| CWE-022 ❌ | 100% | 100% | 0.00 | 4 | 0 | 4 | 0 |
| CWE-078 ❌ | 100% | 100% | 0.00 | 2 | 0 | 2 | 0 |
| CWE-079 ❌ | 100% | 100% | 0.00 | 3 | 0 | 3 | 0 |
| CWE-080 ❌ | 100% | 100% | 0.00 | 1 | 0 | 1 | 0 |
| CWE-089 ✅ | 100% | 0% | 1.00 | 2 | 0 | 0 | 2 |
| CWE-090 ❌ | 100% | 100% | 0.00 | 2 | 0 | 2 | 0 |
| CWE-094 ❌ | 67% | 100% | -0.33 | 2 | 1 | 3 | 0 |
| CWE-095 ❌ | 100% | 100% | 0.00 | 1 | 0 | 1 | 0 |
| CWE-099 ❌ | 0% | 0% | 0.00 | 0 | 1 | 0 | 1 |
| CWE-113 ✅ | 100% | 50% | 0.50 | 2 | 0 | 1 | 1 |
| CWE-116 ❌ | 50% | 50% | 0.00 | 1 | 1 | 1 | 1 |
| CWE-117 ⚠️ | 100% | 67% | 0.33 | 3 | 0 | 2 | 1 |
| CWE-1204 ❌ | 100% | 100% | 0.00 | 1 | 0 | 1 | 0 |
| CWE-193 ❌ | 0% | 0% | 0.00 | 0 | 1 | 0 | 1 |
| CWE-200 ✅ | 100% | 0% | 1.00 | 1 | 0 | 0 | 1 |
| CWE-209 ❌ | 100% | 100% | 0.00 | 1 | 0 | 1 | 0 |
| CWE-215 ✅ | 100% | 50% | 0.50 | 1 | 0 | 1 | 1 |
| CWE-250 ❌ | 100% | 100% | 0.00 | 1 | 0 | 1 | 0 |
| CWE-252 ❌ | 0% | 0% | 0.00 | 0 | 1 | 0 | 1 |
| CWE-259 ❌ | 100% | 100% | 0.00 | 2 | 0 | 2 | 0 |
| CWE-269 ❌ | 100% | 100% | 0.00 | 1 | 0 | 1 | 0 |
| CWE-283 ❌ | 0% | 0% | 0.00 | 0 | 1 | 0 | 1 |
| CWE-285 ❌ | 0% | 0% | 0.00 | 0 | 1 | 0 | 1 |
| CWE-295 ❌ | 67% | 67% | 0.00 | 2 | 1 | 2 | 1 |
| CWE-306 ❌ | 0% | 0% | 0.00 | 0 | 1 | 0 | 1 |
| CWE-319 ❌ | 50% | 50% | 0.00 | 1 | 1 | 1 | 1 |
| CWE-321 ❌ | 100% | 100% | 0.00 | 2 | 0 | 1 | 0 |
| CWE-326 ✅ | 100% | 50% | 0.50 | 2 | 0 | 1 | 1 |
| CWE-327 ✅ | 100% | 50% | 0.50 | 4 | 0 | 2 | 2 |
| CWE-329 ❌ | 100% | 100% | 0.00 | 1 | 0 | 1 | 0 |
| CWE-330 ❌ | 100% | 100% | 0.00 | 1 | 0 | 1 | 0 |
| CWE-331 ❌ | 100% | 100% | 0.00 | 1 | 0 | 1 | 0 |
| CWE-339 ❌ | 0% | 0% | 0.00 | 0 | 1 | 0 | 1 |
| CWE-347 ⚠️ | 100% | 67% | 0.33 | 3 | 0 | 2 | 1 |
| CWE-367 ❌ | 0% | 0% | 0.00 | 0 | 1 | 0 | 1 |
| CWE-377 ❌ | 100% | 100% | 0.00 | 1 | 0 | 1 | 0 |
| CWE-379 ✅ | 100% | 0% | 1.00 | 1 | 0 | 0 | 1 |
| CWE-385 ❌ | 0% | 0% | 0.00 | 0 | 1 | 0 | 1 |
| CWE-400 ❌ | 100% | 100% | 0.00 | 1 | 0 | 1 | 0 |
| CWE-406 ❌ | 0% | 100% | -1.00 | 0 | 1 | 1 | 0 |
| CWE-414 ❌ | 100% | 100% | 0.00 | 1 | 0 | 1 | 0 |
| CWE-425 ✅ | 100% | 0% | 1.00 | 1 | 0 | 0 | 1 |
| CWE-434 ✅ | 50% | 0% | 0.50 | 1 | 1 | 0 | 2 |
| CWE-454 ❌ | 100% | 100% | 0.00 | 1 | 0 | 1 | 0 |
| CWE-462 ❌ | 0% | 0% | 0.00 | 0 | 1 | 0 | 1 |
| CWE-477 ❌ | 100% | 100% | 0.00 | 1 | 0 | 1 | 0 |
| CWE-502 ⚠️ | 100% | 75% | 0.25 | 4 | 0 | 3 | 1 |
| CWE-521 ✅ | 50% | 0% | 0.50 | 1 | 1 | 0 | 2 |
| CWE-522 ✅ | 100% | 50% | 0.50 | 2 | 0 | 1 | 1 |
| CWE-595 ❌ | 0% | 0% | 0.00 | 0 | 1 | 0 | 1 |
| CWE-601 ❌ | 100% | 100% | 0.00 | 5 | 0 | 5 | 0 |
| CWE-605 ❌ | 100% | 100% | 0.00 | 1 | 0 | 1 | 0 |
| CWE-611 ❌ | 100% | 100% | 0.00 | 6 | 0 | 6 | 0 |
| CWE-641 ❌ | 0% | 0% | 0.00 | 0 | 1 | 0 | 1 |
| CWE-643 ❌ | 100% | 100% | 0.00 | 2 | 0 | 2 | 0 |
| CWE-703 ❌ | 33% | 100% | -0.67 | 1 | 2 | 3 | 0 |
| CWE-730 ❌ | 67% | 67% | 0.00 | 2 | 1 | 2 | 1 |
| CWE-732 ❌ | 100% | 100% | 0.00 | 1 | 0 | 1 | 0 |
| CWE-759 ✅ | 100% | 0% | 1.00 | 1 | 0 | 0 | 1 |
| CWE-760 ✅ | 100% | 0% | 1.00 | 1 | 0 | 0 | 1 |
| CWE-776 ❌ | 100% | 100% | 0.00 | 1 | 0 | 1 | 0 |
| CWE-798 ❌ | 100% | 100% | 0.00 | 2 | 0 | 2 | 0 |
| CWE-827 ❌ | 100% | 100% | 0.00 | 1 | 0 | 1 | 0 |
| CWE-835 ✅ | 100% | 0% | 1.00 | 1 | 0 | 0 | 1 |
| CWE-841 ❌ | 0% | 100% | -1.00 | 0 | 1 | 1 | 0 |
| CWE-918 ❌ | 100% | 100% | 0.00 | 2 | 0 | 2 | 0 |
| CWE-941 ❌ | 0% | 100% | -1.00 | 0 | 1 | 1 | 0 |
| CWE-943 ✅ | 100% | 0% | 1.00 | 1 | 0 | 0 | 1 |

## Confirmed Tier Note

The Confirmed Tier shows 0% TPR on this synthetic corpus — this is **expected and correct**.
The Confirmed Tier's four gates (HIGH severity + 22 curated rules + production file path + HIGH Bandit confidence) are calibrated for real production repositories, not for self-contained synthetic micro-files. On the 30-repo production corpus (measured separately), Confirmed Tier achieves **96.4% precision** (CI: [90.9%, 100%]) — the trade-off is *low recall on synthetic files, very high precision on real code*. This is the intended design: the Confirmed Tier is a precision instrument, not a recall instrument.

## How to Reproduce

```bash
# Clone SecurityEval if not present
git clone --depth=1 https://github.com/s2e-lab/SecurityEval TESTS/evaluation/securityeval

# Run — detectable CWE subset
python3 scripts/run_owasp_methodology_benchmark.py \
    --dataset-dir TESTS/evaluation/securityeval

# Run — all CWE classes
python3 scripts/run_owasp_methodology_benchmark.py \
    --dataset-dir TESTS/evaluation/securityeval --all-cwes
```

## Methodology Notes

- **Why Copilot files as TNs?** Copilot completions are security-focused prompts;   the secure ones represent realistic *false-positive targets* — code a developer   would write that should NOT be flagged. This is equivalent to OWASP Benchmark's   non-vulnerable test cases.
- **Why Youden J?** It is the OWASP Benchmark's primary metric: J=0 means random,   J=1 means perfect. It penalizes high FPR as much as low TPR.
- **CWE-level matching** is used throughout — a tool gets credit for flagging a   *file* regardless of which exact line it flags (consistent with SecurityEval   and OWASP Benchmark conventions).
- **Limitations:** This benchmark measures *static detection*. It cannot measure   runtime exploitability — ACR-QA's exploit-verification layer (confirmed tier)   addresses that separately.
