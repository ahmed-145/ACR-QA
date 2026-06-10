# ACR-QA LLM-Augmented Detection Benchmark (held-out)

> **Generated:** 2026-06-03T23:20:44.125192+00:00
> **ACR-QA version:** 5.0.0rc2
> **Repos:** 16 (held-out split)
> **Model:** llama-3.3-70b-versatile
> **Phase:** 1+2 of GO_BIG_LLM_DETECTION_PLAN.md

## Operating-Point Comparison

| Operating Point | Recall | Precision | FPR | Lift |
|---|:---:|:---:|:---:|:---:|
| RULES-ONLY (baseline) | 27.2% | 91.3% | 15.3% | — |
| **LLM-ONLY (raw, ungated)** | **15.6%** | 84.6% | 16.7% | **+-11.6pp** |
| UNION (rules ∪ LLM raw) | 33.6% | 88.2% | 26.4% | +6.4pp |
| **UNION-GATED (gated precision)** | **32.4%** | 89.5% | 22.2% | **+5.2pp** |

## Key Numbers

- **Baseline (rules-only):** 27.2% recall
- **Union lift (raw):** +6.4pp
- **Gated precision:** 89.5%
- **Gated lift retained:** +5.2pp
