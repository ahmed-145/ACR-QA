# T4.2 Bootstrap Confidence Intervals

_Generated: 2026-05-30 12:07 UTC_
_Method: Per-repo bootstrap resampling. Unit of resampling = repo. Each iteration draws N repos with replacement, sums TP/FP/NR, computes precision. 95% CI = 2.5th–97.5th percentile of 10,000 samples._
_n_boot = 10,000, n_repos = 30_

## Summary

| Metric | Point Estimate | 95% CI | CI Width | n repos |
|--------|---------------|--------|----------|---------|
| H/M all-tools, conservative | **8.6%** | [4.5%, 14.0%] | 9.5% | 30 |
| H/M all-tools, optimistic | **22.0%** | [14.8%, 29.2%] | 14.3% | 30 |
| Security-tier, conservative | **25.4%** | [15.1%, 36.5%] | 21.4% | 30 |
| Security-tier, optimistic | **30.0%** | [19.9%, 41.5%] | 21.6% | 30 |
| H/M Python only, conservative | **5.9%** | [3.0%, 9.4%] | 6.5% | 25 |
| H/M JavaScript only, conservative | **18.5%** | [4.1%, 41.2%] | 37.1% | 5 |
| Sec-tier Python only, conservative | **17.4%** | [9.3%, 27.4%] | 18.1% | 25 |
| Sec-tier JS only, conservative | **54.4%** | [45.8%, 66.7%] | 20.8% | 5 |

> **Conservative**: NEEDS_REVIEW → FP.  **Optimistic**: NEEDS_REVIEW → TP.

## Interpretation

### Primary defence number

Security-tier precision: **25.4% [15.1%, 36.5%]** (conservative) / **30.0% [19.9%, 41.5%]** (optimistic).

The 95% confidence interval captures uncertainty arising from the particular
set of repositories in the corpus. If we had sampled a different set of 24
production Python/JS libraries, precision would likely fall within this range.

### H/M blended precision

All-findings H/M precision: **8.6% [4.5%, 14.0%]** (conservative). The wider CI here reflects high variance across repos — some repos generate many low-precision quality findings (radon/vulture) while others are security-heavy.

### Language breakdown

- Python (sec-tier): 17.4% [9.3%, 27.4%] conservative
- JavaScript (sec-tier): 54.4% [45.8%, 66.7%] conservative

JS sec-tier CI is wider (fewer repos) — interpret with more caution.

### CI width interpretation

Security-tier CI width: 21.4% —
a ±10.7pp range. This is expected for a 24-repo precision corpus;
a corpus of 100+ repos would narrow this to under ±5pp.

## Bootstrap Distribution Statistics

| Metric | Mean | Std Dev | CI Width |
|--------|------|---------|---------|
| Security-tier, conservative | 25.5% | ±5.5% | 21.4% |
| Security-tier, optimistic | 30.2% | ±5.5% | 21.6% |
| H/M all-tools, conservative | 8.8% | ±2.5% | 9.5% |

## Summary for Defence

**Q: How reliable are your precision numbers?**

The 95% bootstrap CI for security-tier precision is [15.1%, 36.5%] (conservative) / [19.9%, 41.5%] (optimistic). These CIs are computed by per-repo bootstrap resampling over 30 production repositories with 10,000 iterations. The interval captures corpus-sampling uncertainty — if we re-ran the benchmark on a different set of production libraries, we would expect precision to fall in this range with 95% probability.
