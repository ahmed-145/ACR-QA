# ACR-QA OWASP-Methodology Python Benchmark

> **Generated:** 2026-06-02T23:38:12.984586+00:00
> **ACR-QA version:** 5.0.0rc1
> **Corpus:** SecurityEval (Insecure_Code = TPs, Copilot = TNs)
> **Scope:** Statically-detectable CWE subset
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
| **ACR-QA (full output)** | **91.0%** [84.3%, 96.6%] | 75.3% | **0.157** [4.5%, 27.0%] | 0.210 | 54.7% | 68.4% |
| Bandit (standalone) | 50.6% [40.4%, 61.8%] | 41.6% | 0.090 [-4.5%, 24.7%] | 0.090 | 54.9% | 52.6% |
| Semgrep CE (standalone) | 23.6% [15.7%, 32.6%] | 18.0% | 0.056 [-5.6%, 18.0%] | 0.069 | 56.8% | 33.3% |
| ACR-QA (Confirmed Tier) | 0.0% [0.0%, 0.0%] | 0.0% | 0.000 [0.0%, 0.0%] | 0.000 | 0.0% | 0.0% |

**Industry baselines (Java OWASP Benchmark 2024 — different language, context only):**

| Tool | TPR | FPR | Youden J |
|------|:---:|:---:|:---:|
| SonarQube | 50% | 35% | 0.15 |
| Checkmarx | 62% | 51% | 0.11 |
| FindBugs/SpotBugs | 52% | 6% | 0.46 |

## Sample sizes

- **TP corpus** (Insecure_Code): 89 files
- **TN corpus** (Copilot): 89 files
- **Total**: 178 labeled files

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
| CWE-113 ✅ | 100% | 50% | 0.50 | 2 | 0 | 1 | 1 |
| CWE-116 ❌ | 50% | 50% | 0.00 | 1 | 1 | 1 | 1 |
| CWE-117 ⚠️ | 100% | 67% | 0.33 | 3 | 0 | 2 | 1 |
| CWE-200 ✅ | 100% | 0% | 1.00 | 1 | 0 | 0 | 1 |
| CWE-209 ❌ | 100% | 100% | 0.00 | 1 | 0 | 1 | 0 |
| CWE-259 ❌ | 100% | 100% | 0.00 | 2 | 0 | 2 | 0 |
| CWE-295 ❌ | 67% | 67% | 0.00 | 2 | 1 | 2 | 1 |
| CWE-319 ❌ | 50% | 50% | 0.00 | 1 | 1 | 1 | 1 |
| CWE-321 ❌ | 100% | 100% | 0.00 | 2 | 0 | 1 | 0 |
| CWE-326 ✅ | 100% | 50% | 0.50 | 2 | 0 | 1 | 1 |
| CWE-327 ✅ | 100% | 50% | 0.50 | 4 | 0 | 2 | 2 |
| CWE-329 ❌ | 100% | 100% | 0.00 | 1 | 0 | 1 | 0 |
| CWE-330 ❌ | 100% | 100% | 0.00 | 1 | 0 | 1 | 0 |
| CWE-331 ❌ | 100% | 100% | 0.00 | 1 | 0 | 1 | 0 |
| CWE-347 ⚠️ | 100% | 67% | 0.33 | 3 | 0 | 2 | 1 |
| CWE-377 ❌ | 100% | 100% | 0.00 | 1 | 0 | 1 | 0 |
| CWE-379 ✅ | 100% | 0% | 1.00 | 1 | 0 | 0 | 1 |
| CWE-502 ⚠️ | 100% | 75% | 0.25 | 4 | 0 | 3 | 1 |
| CWE-521 ✅ | 50% | 0% | 0.50 | 1 | 1 | 0 | 2 |
| CWE-595 ❌ | 0% | 0% | 0.00 | 0 | 1 | 0 | 1 |
| CWE-601 ❌ | 100% | 100% | 0.00 | 5 | 0 | 5 | 0 |
| CWE-605 ❌ | 100% | 100% | 0.00 | 1 | 0 | 1 | 0 |
| CWE-611 ❌ | 100% | 100% | 0.00 | 6 | 0 | 6 | 0 |
| CWE-730 ❌ | 67% | 67% | 0.00 | 2 | 1 | 2 | 1 |
| CWE-732 ❌ | 100% | 100% | 0.00 | 1 | 0 | 1 | 0 |
| CWE-759 ✅ | 100% | 0% | 1.00 | 1 | 0 | 0 | 1 |
| CWE-760 ✅ | 100% | 0% | 1.00 | 1 | 0 | 0 | 1 |
| CWE-776 ❌ | 100% | 100% | 0.00 | 1 | 0 | 1 | 0 |
| CWE-798 ❌ | 100% | 100% | 0.00 | 2 | 0 | 2 | 0 |
| CWE-835 ✅ | 100% | 0% | 1.00 | 1 | 0 | 0 | 1 |
| CWE-918 ❌ | 100% | 100% | 0.00 | 2 | 0 | 2 | 0 |
| CWE-941 ❌ | 0% | 100% | -1.00 | 0 | 1 | 1 | 0 |
| CWE-943 ✅ | 100% | 0% | 1.00 | 1 | 0 | 0 | 1 |

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
