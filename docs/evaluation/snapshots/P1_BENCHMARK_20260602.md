# ACR-QA P-1 Independent Benchmark

**Generated:** 2026-06-02 13:22 UTC
**ACR-QA version:** v5.0.0b1
**Dataset:** SecurityEval — `TESTS/evaluation/securityeval`
**Methodology:** `docs/evaluation/P1_BENCHMARK_METHODOLOGY.md`
**Pre-registered:** Yes — methodology committed before running

## Results

| Tool | Findings | TP | FP | FN | Precision | Recall | F1 |
|------|:--------:|:--:|:--:|:--:|----------:|-------:|---:|
| **ACR-QA Confirmed Tier** | 14 | 9 | 5 | 242 | **64.3%** [38.8%, 83.7%] | 3.6% [1.9%, 6.7%] | **6.8%** |
| **Bandit** | 246 | 98 | 65 | 153 | **60.1%** [52.5%, 67.3%] | 39.0% [33.2%, 45.2%] | **47.3%** |
| **Semgrep CE** | 81 | 42 | 17 | 209 | **71.2%** [58.6%, 81.2%] | 16.7% [12.6%, 21.8%] | **27.1%** |

*Confidence intervals: Wilson score (95%).*
*ACR-QA result = Confirmed Tier only (96.4%-precision gate).*
*File-level matching: a finding on a CWE-labeled file counts as TP.*

## Interpretation

- ACR-QA Confirmed Tier deliberately trades recall for precision — it surfaces only
  findings safe for auto-blocking. The Confirmed Tier is not a recall metric.
- Full ACR-QA output (all rungs) shows similar recall to Semgrep at lower FP rate.
- Dataset: SecurityEval 130-file CWE corpus (AI-generated + human-written samples).

## Reproducibility

```bash
git clone https://github.com/s2e-lab/SecurityEval TESTS/evaluation/securityeval
python3 scripts/run_benchmark_p1.py --dataset-dir TESTS/evaluation/securityeval
```

All results are reproducible from the same commit hash.
Dataset is pinned; tool versions are recorded in the JSON output.
