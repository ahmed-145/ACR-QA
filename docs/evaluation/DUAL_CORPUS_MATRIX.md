# T4.3 Dual-Corpus Confusion Matrix

_Generated: 2026-05-29 19:51 UTC_

Dual-corpus evaluation: precision corpus measures FP rate on clean production libraries; recall corpus measures detection rate on known-vulnerable apps pinned to CVE-introducing commits.

## The 2×2 View

| | ACR-QA flags a finding | ACR-QA does not flag | Notes |
|---|---|---|---|
| **Known vulnerability (recall corpus)** | **TP: 11 CVEs** | FN: 0 detectable miss | +2 honest misses (not detectable) |
| **No known vulnerability (precision corpus)** | FP: 194 findings | TN: rest of corpus | Security-tier only (219 findings evaluated) |

> **Row 1**: recall corpus — 25 CVEs across 25 commits (Track 1 + Track 2).
> **Row 2**: precision corpus — 24 clean production repos (1942 post-dedup findings).

## Recall Corpus — CVE Detection

### Track 1 (20 CVEs, 8 detectable)

- CVEs tested: 20
- Detectable by static analysis: 8
- Detected (TP): **8**
- Missed (FN): **0**
- Clean repos (TN): 12

Detected CVEs:
- Werkzeug@0.11.10
- PyYAML@3.13
- celery@5.2.1
- GitPython@3.1.26
- PyYAML@5.3.1
- cookiecutter@1.7.3
- Pillow@9.0.0rc2
- dask@2021.9.1

### Track 2 (5 CVEs, 3 detectable, 2 honest misses)

- CVEs tested: 5
- Detectable: 3
- Detected (TP): **3** — families: SSTI (CWE-1336), XXE (CWE-611), XXE (CWE-611)
- Genuine FN: **0**
- Honest misses (not detectable by static analysis): SQLi (CWE-89), SQLi (CWE-89)

### Combined Recall

| Metric | Value |
|--------|-------|
| Detectable CVEs | 11 |
| Detected (TP) | **11** |
| Missed (FN) | **0** |
| Honest misses (undetectable) | 2 |
| **Recall (detectable)** | **100.0%** |
| Recall (all including honest miss) | 84.6% |

## Precision Corpus — False Positive Analysis

| Metric | Conservative | Optimistic |
|--------|-------------|-----------|
| H/M all-tools precision | 8.6% [4.5%, 13.9%] | 28.1% [19.6%, 36.6%] |
| Security-tier precision | **24.7%** [14.6%, 35.4%] | **37.9%** [26.4%, 50.4%] |

Security-tier findings: 219 (54 TP / 165 FP / 29 NR)

## The F1 Perspective

F1 = 2 × (Precision × Recall) / (Precision + Recall) at the security-tier:

| Precision mode | Precision | Recall | F1 |
|----------------|-----------|--------|-----|
| Conservative | 24.7% | 100.0% | **39.6%** |
| Optimistic | 37.9% | 100.0% | **55.0%** |

> Note: F1 mixes finding-level (precision) and CVE-level (recall) metrics.
> These are different denominator units — treat as indicative, not cardinal.

## Honest Misses — Why We Can't Detect Some CVEs

The 2 honest misses from Track 2 are not bugs in ACR-QA:

| CVE | Package | Reason undetectable |
|-----|---------|---------------------|
| CVE-2024-36039 | PyMySQL@v1.1.0 | Internal `escape_dict()` omits key escaping — not visible at call site; requires taint analysis of ORM internals |
| CVE-2024-42005 | Django@4.2.14 | ORM-internal SQL column alias construction — application call site has no detectable pattern |

Both require semantic understanding of ORM internals that pattern-based and shallow-taint tools cannot achieve. This is a documented limitation of the static analysis approach, not a correctness failure.

## Summary for Defence

ACR-QA detects 11/11 statically-detectable CVEs (recall = 100%) while maintaining 24.7%–37.9% precision on the security-tier (CI: [14.6%, 35.4%] conservative). 2 CVEs are honest misses (not detectable by static pattern analysis).

| Dimension | Metric | Value |
|-----------|--------|-------|
| **Recall** | CVE detection rate (detectable) | **100.0%** (11/11) |
| **Precision** | Security-tier (conservative) | **24.7%** [14.6%, 35.4%] |
| **Precision** | Security-tier (optimistic) | **37.9%** [26.4%, 50.4%] |
| **F1** | Conservative | **39.6%** |
| **F1** | Optimistic | **55.0%** |
| Honest misses | Undetectable by static analysis | 2 CVEs documented |
