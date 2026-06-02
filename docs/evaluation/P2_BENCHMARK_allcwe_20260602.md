# ACR-QA P-2 Rigorous Benchmark — Recall on Genuinely-Vulnerable Code

**Generated:** 2026-06-02 17:21 UTC
**ACR-QA version:** v5.0.0b1
**Corpus:** SecurityEval `Testcases_Insecure_Code/` — curated, genuinely-vulnerable samples
**CWE scope:** all CWE classes (121 files)
**Metric:** recall = flagged / total (every file is a known true positive)
**CIs:** bootstrap 95% (1,000 resamples, seed=42)

## Why this supersedes P-1

P-1 used `Testcases_Copilot/`, which are Copilot *completions* — frequently **secure**
(e.g. parameterized SQL). Counting a tool's correct silence on secure code as a miss is
wrong ground truth, which is why P-1's recall (3.6%) was meaningless. P-2 uses the curated
insecure corpus where every file is genuinely vulnerable, runs ACR-QA's *full* detection
(incl. custom Semgrep rules), and restricts to CWEs that static analysis can actually detect.

## Results

| Tool | Recall | 95% CI | Detected / Total |
|------|-------:|--------|:----------------:|
| **ACR-QA (full output)** | **55.4%** | [47.1%, 64.5%] | 67/121 |
| **ACR-QA (Confirmed Tier)** | **5.0%** | [1.7%, 9.1%] | 6/121 |
| Bandit (standalone) | 44.6% | [35.5%, 53.7%] | 54/121 |
| Semgrep CE (standalone) | 19.0% | [12.4%, 26.4%] | 23/121 |

*ACR-QA full output = all findings. Confirmed Tier = the auto-block-safe subset.*

## Per-CWE detection (ACR-QA full output)

| CWE | Detected | Total |
|-----|:--------:|:-----:|
| CWE-020 | 3 | 6 |
| CWE-022 | 3 | 4 |
| CWE-078 | 2 | 2 |
| CWE-079 | 1 | 3 |
| CWE-080 | 1 | 1 |
| CWE-089 | 2 | 2 |
| CWE-090 | 0 | 2 |
| CWE-094 | 2 | 3 |
| CWE-095 | 1 | 1 |
| CWE-099 | 0 | 1 |
| CWE-113 | 0 | 2 |
| CWE-116 | 1 | 2 |
| CWE-117 | 0 | 3 |
| CWE-1204 | 1 | 1 |
| CWE-193 | 0 | 1 |
| CWE-200 | 1 | 1 |
| CWE-209 | 0 | 1 |
| CWE-215 | 1 | 1 |
| CWE-250 | 1 | 1 |
| CWE-252 | 0 | 1 |
| CWE-259 | 2 | 2 |
| CWE-269 | 1 | 1 |
| CWE-283 | 0 | 1 |
| CWE-285 | 0 | 1 |
| CWE-295 | 1 | 3 |
| CWE-306 | 0 | 1 |
| CWE-319 | 1 | 2 |
| CWE-321 | 1 | 2 |
| CWE-326 | 2 | 2 |
| CWE-327 | 3 | 4 |
| CWE-329 | 1 | 1 |
| CWE-330 | 1 | 1 |
| CWE-331 | 1 | 1 |
| CWE-339 | 0 | 1 |
| CWE-347 | 1 | 3 |
| CWE-367 | 0 | 1 |
| CWE-377 | 1 | 1 |
| CWE-379 | 1 | 1 |
| CWE-385 | 0 | 1 |
| CWE-400 | 0 | 1 |
| CWE-406 | 0 | 1 |
| CWE-414 | 1 | 1 |
| CWE-425 | 1 | 1 |
| CWE-434 | 1 | 2 |
| CWE-454 | 1 | 1 |
| CWE-462 | 0 | 1 |
| CWE-477 | 1 | 1 |
| CWE-502 | 4 | 4 |
| CWE-521 | 0 | 2 |
| CWE-522 | 2 | 2 |
| CWE-595 | 0 | 1 |
| CWE-601 | 1 | 5 |
| CWE-605 | 1 | 1 |
| CWE-611 | 6 | 6 |
| CWE-641 | 0 | 1 |
| CWE-643 | 2 | 2 |
| CWE-703 | 1 | 3 |
| CWE-730 | 0 | 3 |
| CWE-732 | 1 | 1 |
| CWE-759 | 1 | 1 |
| CWE-760 | 0 | 1 |
| CWE-776 | 1 | 1 |
| CWE-798 | 2 | 2 |
| CWE-827 | 1 | 1 |
| CWE-835 | 0 | 1 |
| CWE-841 | 0 | 1 |
| CWE-918 | 2 | 2 |
| CWE-941 | 0 | 1 |
| CWE-943 | 0 | 1 |

## Reproduce

```bash
git clone https://github.com/s2e-lab/SecurityEval TESTS/evaluation/securityeval
python3 scripts/run_benchmark_p2.py --dataset-dir TESTS/evaluation/securityeval
```
