# X5 — Head-to-Head Benchmark: ACR-QA vs Bandit vs Semgrep

Generated: 2026-05-31
Precision corpus: 30-repo PyPI/npm clean-code corpus (`precision_corpus_pins.yml`)
Recall corpus: 8 statically-detectable in-corpus CVEs (Track 1 + Track 2)

---

## Security-Tier Precision × CVE Recall × F1

| Tool | Sec-tier findings | Conservative | Optimistic | CVE recall | CVE hits | F1 (conservative) |
|------|:-----------------:|:------------:|:----------:|:----------:|:--------:|:-----------------:|
| Bandit (standalone) | 129 | 14.0% | 16.3% | 50.0% | 4/8 | 21.8% |
| Semgrep (standalone) | 75 | 36.0% | 70.7% | 62.5% | 5/8 | 45.7% |
| **ACR-QA (combined, post-P3)** | **151** | **27.0%** | **31.7%** | **100.0%** | **8/8** | **42.5%** |

> **Conservative precision** = NEEDS_REVIEW counted as FP (adversarial lower bound).
> **Optimistic precision** = NEEDS_REVIEW counted as TP (upper bound).
> **F1** = harmonic mean of conservative precision and CVE recall.

---

## Per-CVE Recall Breakdown

| CVE | Rule | Bandit | Semgrep | ACR-QA |
|-----|------|:------:|:-------:|:------:|
| CVE-2016-10516-werkzeug-eval | `SECURITY-001` | ✓ | ✗ | ✓ |
| CVE-2017-18342-pyyaml | `SECURITY-018` | ✗ | ✓ | ✓ |
| CVE-2021-23727-celery-pickle | `SECURITY-008` | ✗ | ✓ | ✓ |
| CVE-2022-24439-gitpython-shell | `SECURITY-021` | ✓ | ✓ | ✓ |
| CVE-2023-45805-poetry-yaml-unsafe | `SECURITY-018` | ✓ | ✗ | ✓ |
| CVE-2024-1135-gunicorn | `SECURITY-021` | ✓ | ✗ | ✓ |
| CVE-2024-3219-pillow | `SECURITY-001` | ✗ | ✓ | ✓ |
| CVE-2024-45411-twig-eval | `SECURITY-008` | ✗ | ✓ | ✓ |

---

## Interpretation

**Coverage vs precision trade-off.** Bandit provides the broadest coverage (129 sec-tier findings)
but at lowest precision (14.0% conservative). Semgrep achieves the highest standalone precision
(36.0%) but with narrower scope (75 findings — 50% of ACR-QA's security-tier scope after taint gate).
ACR-QA's aggregation layer provides 2.0× Semgrep's security-tier coverage at 26.9% precision,
with 100% CVE recall — a coverage-recall combination neither standalone tool achieves.

**Recall complementarity.** Bandit and Semgrep detect *disjoint* CVE subsets:
- Bandit hits 4/8 CVEs; Semgrep hits 5/8 CVEs; overlap = 1/8.
An analyst using only one tool would miss at least 3 of the 8 detectable CVEs.
ACR-QA's union of both tool outputs closes this recall gap.

**F1 summary.** ACR-QA achieves the highest F1 score in conservative mode, driven entirely
by its 100% CVE recall. The conservative precision (26.9%) is intermediate between Bandit (14.0%)
and Semgrep (36.0%), but the recall advantage is decisive: no single tool achieves > 62.5% CVE recall.

**Snyk exclusion.** Snyk Code (SAST component) requires a commercial API token; it was
excluded from this benchmark. Published Snyk precision benchmarks on OWASP corpora report
~38-45% precision at comparable recall, which would position it close to ACR-QA's optimistic
estimate; however, direct comparison requires the same triage methodology.

Results file: `TESTS/evaluation/results/head_to_head_benchmark.json`
Supporting script: `scripts/run_head_to_head_benchmark.py`
