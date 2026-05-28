# Precision Benchmark — ACR-QA v5.0

*Generated: 2026-05-28 20:04 UTC*
*Corpus: [`precision_corpus_pins.yml`](../../TESTS/evaluation/precision_corpus_pins.yml)*

---

## Summary

| Metric | Conservative | Optimistic |
|--------|-------------|-----------|
| **Precision** | **5.7%** | **20.5%** |
| TP | 54 | 193 |
| FP | 887 | 748 |
| Needs Review | 139 | 139 |
| Total H/M findings | 941 | 941 |
| Repos scanned | 24 | — |

> **Conservative**: `NEEDS_REVIEW` items counted as FP (worst-case precision).
> **Optimistic**: `NEEDS_REVIEW` items counted as TP (best-case precision).
> True precision lies between these bounds pending manual review.

---

## Methodology

### Corpus selection

30 mature, actively-maintained production repos selected by objective popularity ranking:

| Language | Count | Ranking criterion |
|----------|-------|-------------------|
| Python | 20 | Top-20 PyPI 30-day downloads (hugovk.dev snapshot 2026-05-28) |
| JavaScript/TypeScript | 6 | Top-6 GitHub stars (snapshot 2026-05-28), installable libs/frameworks only |
| Go | 4 | Top-4 GitHub stars (snapshot 2026-05-28), installable libs/apps only |

Star-farmed repos (stars >> forks, no recognizable npm/go-install audience) were excluded.

### Precision measurement logic

1. Scan each repo with `python -m CORE --no-ai --json` (AI explanations disabled for speed).
2. Filter to **HIGH** and **MEDIUM** severity findings only (LOW excluded from denominator).
3. Auto-triage each finding:
   - **AUTO_FP** if file path matches test / vendor / example patterns, or rule is a low-signal quality rule.
   - **AUTO_TP** if rule is in `HIGH_CONFIDENCE_RULES` set and severity is HIGH and file is production code.
   - **NEEDS_REVIEW** otherwise (ambiguous — requires human judgment).
4. Compute conservative precision (NEEDS_REVIEW → FP) and optimistic precision (NEEDS_REVIEW → TP).

### Interpretation

These repos receive continuous security review from expert maintainers.
A genuine TP finding from ACR-QA on these codebases would be a **security contribution**, not noise.
The FP rate here represents the tool's noise floor on clean, well-maintained production code.

---

## Language breakdown

| Language       | H/M   |  TP  |  FP  |  NR | Conservative | Optimistic |
|----------------|-------|------|------|-----|-------------|-----------|
| Python         |   573 |   29 |  430 | 114 |     5.1% |     25.0% |
| Javascript     |   368 |   25 |  318 |  25 |     6.8% |     13.6% |

---

## Per-repo results

| Repo                     | Language     | Total  | H/M  | TP | FP | NR |
|--------------------------|--------------|--------|------|----|----|----|
| packaging                | python       |     30 |   20 |  3 | 17 |  0 |
| urllib3                  | python       |     36 |   16 |  0 | 14 |  2 |
| requests                 | python       |     65 |   23 |  0 | 23 |  0 |
| charset-normalizer       | python       |     60 |   10 |  0 | 10 |  0 |
| setuptools               | python       |     32 |   32 |  7 | 16 |  9 |
| cryptography             | python       |      0 |    0 |  0 |  0 |  0 |
| python-dateutil          | python       |    114 |   36 |  0 | 26 | 10 |
| pyyaml                   | python       |     55 |   35 |  0 | 34 |  1 |
| pydantic                 | python       |     51 |   51 |  3 | 42 |  6 |
| pygments                 | python       |     71 |   50 |  2 | 26 | 22 |
| click                    | python       |     63 |   21 |  1 | 11 |  9 |
| numpy                    | python       |     24 |   24 |  2 | 20 |  2 |
| pycparser                | python       |     60 |    9 |  0 |  8 |  1 |
| anyio                    | python       |     58 |   24 |  4 | 16 |  4 |
| attrs                    | python       |     69 |   24 |  1 | 23 |  0 |
| h11                      | python       |     75 |   25 |  0 | 19 |  6 |
| fsspec                   | python       |     96 |   65 |  0 | 49 | 16 |
| pytest                   | python       |     65 |   48 |  4 | 30 | 14 |
| pandas                   | python       |     34 |   34 |  2 | 21 | 11 |
| httpx                    | python       |     81 |   26 |  0 | 25 |  1 |
| axios                    | javascript   |    300 |   14 |  7 |  1 |  6 |
| express                  | javascript   |    298 |  298 |  0 | 288 | 10 |
| nextjs                   | javascript   |     23 |   18 |  6 | 10 |  2 |
| react                    | javascript   |      0 |    0 |  0 |  0 |  0 |
| webpack                  | javascript   |    238 |   28 | 10 | 16 |  2 |
| n8n                      | javascript   |     21 |   10 |  2 |  3 |  5 |
| gin                      | go           |      0 |    0 |  0 |  0 |  0 |
| caddy                    | go           |      0 |    0 |  0 |  0 |  0 |
| syncthing                | go           |      0 |    0 |  0 |  0 |  0 |
| frp                      | go           |      0 |    0 |  0 |  0 |  0 |

---

## Auto-triage heuristics

### AUTO_FP triggers
- File path matches: `tests?/`, `spec/`, `fixtures/`, `examples?/`, `vendor/`, `node_modules/`, `benchmarks?/`, `docs/`, `migrations/`
- Rule ID in low-signal set: `QUALITY-*`, `COMPLEXITY-*`, `DEAD-001`
- Message contains `# nosec`, `# noqa`, or explicit "safe use" note

### AUTO_TP triggers
- Severity = HIGH **and** rule in high-confidence set (`SECURITY-*`, `SECRET-*`, `SQLI-*`, `SHELL-*`, `YAML-001`, `XML-001`, `CRYPTO-*`) **and** file is not test/vendor

### NEEDS_REVIEW
- All findings not matching above — require human judgment to classify.
- Raw data in [`precision_triage.json`](../../TESTS/evaluation/results/precision_triage.json).

---

## Recall (existing CVE battery)

Recall is measured separately on the CVE recall corpus (intentionally vulnerable repos).
See [`CVE_RECALL.md`](CVE_RECALL.md) and [`eval_summary.json`](../../TESTS/evaluation/results/eval_summary.json).

| Metric | Value |
|--------|-------|
| CVE recall | **100%** (8/8 detectable CVEs found) |
| Total CVE tests | 20 (8 detectable, 12 correctly return 0) |

---

*Triage worksheet: `TESTS/evaluation/results/precision_triage.json`*
*Full summary: `TESTS/evaluation/results/precision_summary.json`*
