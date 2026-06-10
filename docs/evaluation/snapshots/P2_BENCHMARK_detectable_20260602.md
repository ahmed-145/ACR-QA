# ACR-QA P-2 Rigorous Benchmark — Recall on Genuinely-Vulnerable Code

**Generated:** 2026-06-02 22:24 UTC
**ACR-QA version:** v5.0.0b1
**Corpus:** SecurityEval `Testcases_Insecure_Code/` — curated, genuinely-vulnerable samples
**CWE scope:** statically-detectable CWE subset (89 files)
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
| **ACR-QA (full output)** | **91.0%** | [84.3%, 96.6%] | 81/89 |
| **ACR-QA (Confirmed Tier)** | **5.6%** | [1.1%, 11.2%] | 5/89 |
| Bandit (standalone) | 50.6% | [39.3%, 60.7%] | 45/89 |
| Semgrep CE (standalone) | 23.6% | [14.6%, 32.6%] | 21/89 |

*ACR-QA full output = all findings. Confirmed Tier = the auto-block-safe subset.*

## Per-CWE detection (ACR-QA full output)

| CWE | Detected | Total |
|-----|:--------:|:-----:|
| CWE-020 | 6 | 6 |
| CWE-022 | 4 | 4 |
| CWE-078 | 2 | 2 |
| CWE-079 | 3 | 3 |
| CWE-080 | 1 | 1 |
| CWE-089 | 2 | 2 |
| CWE-090 | 2 | 2 |
| CWE-094 | 2 | 3 |
| CWE-095 | 1 | 1 |
| CWE-113 | 2 | 2 |
| CWE-116 | 1 | 2 |
| CWE-117 | 3 | 3 |
| CWE-200 | 1 | 1 |
| CWE-209 | 1 | 1 |
| CWE-259 | 2 | 2 |
| CWE-295 | 2 | 3 |
| CWE-319 | 1 | 2 |
| CWE-321 | 2 | 2 |
| CWE-326 | 2 | 2 |
| CWE-327 | 4 | 4 |
| CWE-329 | 1 | 1 |
| CWE-330 | 1 | 1 |
| CWE-331 | 1 | 1 |
| CWE-347 | 3 | 3 |
| CWE-377 | 1 | 1 |
| CWE-379 | 1 | 1 |
| CWE-502 | 4 | 4 |
| CWE-521 | 1 | 2 |
| CWE-595 | 0 | 1 |
| CWE-601 | 5 | 5 |
| CWE-605 | 1 | 1 |
| CWE-611 | 6 | 6 |
| CWE-730 | 2 | 3 |
| CWE-732 | 1 | 1 |
| CWE-759 | 1 | 1 |
| CWE-760 | 1 | 1 |
| CWE-776 | 1 | 1 |
| CWE-798 | 2 | 2 |
| CWE-835 | 1 | 1 |
| CWE-918 | 2 | 2 |
| CWE-941 | 0 | 1 |
| CWE-943 | 1 | 1 |

## Reproduce

```bash
git clone https://github.com/s2e-lab/SecurityEval TESTS/evaluation/securityeval
python3 scripts/run_benchmark_p2.py --dataset-dir TESTS/evaluation/securityeval
```
