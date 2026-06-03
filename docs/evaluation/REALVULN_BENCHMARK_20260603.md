# ACR-QA RealVuln Benchmark

> **Generated:** 2026-06-03T13:25:36.683846+00:00
> **ACR-QA version:** 5.0.0rc2
> **Corpus:** RealVuln (kolega-ai/Real-Vuln-Benchmark)
> **Repos:** 22/26 cloned (4 GitHub URLs broken in manifest)
> **Methodology:** file + CWE + line (±10) matching; F2/F3 (recall-weighted); MCC

## Why RealVuln

RealVuln uses **real production Python apps** (not synthetic snippets) with hand-labelled
TP and FP traps — designed specifically to resist SAST gaming. Each ground-truth entry
lists `acceptable_cwes` (CWE families that count), `is_vulnerable` (TP vs FP trap),
and file+line location. Scoring requires correct CWE *and* file *and* line (±10).

This directly addresses the 'benchmarked themselves' objection: the corpus is from a
third-party lab, uses real multi-file applications, and includes FP traps.

## Aggregate Results

| Tool | Recall | FPR | F3 | MCC | Youden J |
|------|:---:|:---:|:---:|:---:|:---:|
| **ACR-QA (Bandit + Semgrep + custom)** | **23.5%** | 15.5% | **0.254** | 0.068 | 0.080 |
| Bandit (standalone) | 18.3% | 13.4% | 0.199 | 0.045 | 0.049 |

## Per-Repo Recall (ACR-QA full output)

| Repo | GT TPs | GT FPs | TP | FP | FN | Recall | F3 |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| intentionally-vulnerable-python-app | 7 | 2 | 5 | 2 | 2 | 71% | 0.714 |
| vfapi | 9 | 2 | 6 | 0 | 3 | 67% | 0.690 |
| pythonssti | 2 | 1 | 1 | 1 | 1 | 50% | 0.500 |
| insecure-web | 9 | 2 | 4 | 1 | 5 | 44% | 0.465 |
| vulnerable-flask-app | 21 | 4 | 9 | 0 | 12 | 43% | 0.455 |
| dvblab | 22 | 4 | 9 | 1 | 13 | 41% | 0.433 |
| damn-vulnerable-flask-application | 15 | 4 | 6 | 1 | 9 | 40% | 0.422 |
| python-insecure-app | 8 | 2 | 3 | 0 | 5 | 38% | 0.400 |
| vulpy | 57 | 6 | 15 | 1 | 42 | 26% | 0.284 |
| djangoat | 50 | 6 | 13 | 0 | 37 | 26% | 0.281 |
| vulnerable-python-apps | 22 | 5 | 5 | 0 | 17 | 23% | 0.246 |
| dsvw | 27 | 4 | 6 | 2 | 21 | 22% | 0.239 |
| dsvpwa | 32 | 6 | 7 | 1 | 25 | 22% | 0.236 |
| vulnpy | 78 | 16 | 17 | 4 | 61 | 22% | 0.235 |
| lets-be-bad-guys | 24 | 4 | 4 | 0 | 20 | 17% | 0.182 |
| extremely-vulnerable-flask-app | 32 | 4 | 5 | 0 | 27 | 16% | 0.171 |
| threatbyte | 26 | 5 | 4 | 1 | 22 | 15% | 0.167 |
| dvpwa | 22 | 4 | 3 | 0 | 19 | 14% | 0.149 |
| vampi | 15 | 4 | 2 | 0 | 13 | 13% | 0.146 |
| damn-vulnerable-graphql-application | 36 | 4 | 4 | 0 | 32 | 11% | 0.122 |
| flask-xss | 30 | 5 | 3 | 0 | 27 | 10% | 0.110 |
| vulnerable-tornado-app | 14 | 3 | 0 | 0 | 14 | 0% | 0.000 |

## Matching Methodology

A finding is a **TP** if all three match:
1. **File:** finding file path ends-with or equals the GT file path
2. **CWE:** finding CWE is in the GT's `acceptable_cwes` list
3. **Line:** finding line is within ±10 of the GT start_line

A **FP** is a finding that matches a GT entry with `is_vulnerable=false`.
FN = GT TPs that no finding matched. TN = GT FP-traps that no finding matched.

## Reproduce

```bash
# Clone repos (one-time)
cd TESTS/evaluation/realvuln && python3 clone_repos.py

# Run benchmark
python3 scripts/run_realvuln_benchmark.py
```
