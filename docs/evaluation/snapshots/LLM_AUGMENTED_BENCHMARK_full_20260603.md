# ACR-QA LLM-Augmented Detection Benchmark (full)

> **Generated:** 2026-06-03T23:51:13.261523+00:00
> **ACR-QA version:** 5.0.0rc2
> **Repos:** 22 (full split)
> **Model:** llama-3.3-70b-versatile
> **Phase:** 1+2 of GO_BIG_LLM_DETECTION_PLAN.md

## Operating-Point Comparison

| Operating Point | Recall | Precision | FPR | Lift |
|---|:---:|:---:|:---:|:---:|
| RULES-ONLY (baseline) | 25.1% | 90.3% | 15.5% | — |
| **LLM-ONLY (raw, ungated)** | **16.5%** | 85.2% | 16.5% | **+-8.6pp** |
| UNION (rules ∪ LLM raw) | 32.4% | 87.4% | 26.8% | +7.4pp |
| **UNION-GATED (gated precision)** | **31.2%** | 89.2% | 21.6% | **+6.1pp** |

## Key Numbers

- **Baseline (rules-only):** 25.1% recall
- **Union lift (raw):** +7.4pp
- **Gated precision:** 89.2%
- **Gated lift retained:** +6.1pp
