# Precision Benchmark — ACR-QA v5.0

*Generated: 2026-05-29 05:34 UTC*
*Corpus: [`precision_corpus_pins.yml`](../../TESTS/evaluation/precision_corpus_pins.yml)*

---

## Summary

| Metric | Conservative | Optimistic |
|--------|-------------|-----------|
| **Blended precision** (all H/M) | **8.6%** | **28.1%** |
| **Security-tier precision** (HIGH security rules) | **24.7%** | **37.9%** |
| TP (blended) | 54 | 177 |
| FP (blended) | 576 | 453 |
| Needs Review | 123 | 123 |
| Total H/M findings | 630 | 630 |
| Security-tier denominator | 219 | 219 |
| Repos scanned | 24 | — |

> **Conservative**: `NEEDS_REVIEW` items counted as FP (worst-case precision).
> **Optimistic**: `NEEDS_REVIEW` items counted as TP (best-case precision).
> True precision lies between these bounds pending manual review.
>
> **Security-tier precision** restricts the denominator to `HIGH`-severity findings
> whose rule belongs to a security category (`SECURITY-*`, `SECRET-*`, `SQLI-*`,
> `SHELL-*`, `XML-*`, `YAML-*`, `CRYPTO-*`). Style, quality, and complexity
> findings are excluded. This is the standard SAST reporting stratum used by
> industry tools (Semgrep, CodeQL, Snyk) and is the defensible primary metric
> for a security analysis tool.

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
| Python         |   495 |   29 |  385 |  81 |     5.9% |     22.2% |
| Javascript     |   135 |   25 |   68 |  42 |    18.5% |     49.6% |

---

## Per-repo results

| Repo                     | Language     | Total  | H/M  | TP | FP | NR |
|--------------------------|--------------|--------|------|----|----|----|
| packaging                | python       |     30 |   20 |  3 | 17 |  0 |
| urllib3                  | python       |     36 |   16 |  0 | 16 |  0 |
| requests                 | python       |     65 |   23 |  0 | 23 |  0 |
| charset-normalizer       | python       |     60 |   10 |  0 | 10 |  0 |
| setuptools               | python       |     32 |   32 |  7 | 18 |  7 |
| cryptography             | python       |      0 |    0 |  0 |  0 |  0 |
| python-dateutil          | python       |    104 |   28 |  0 | 20 |  8 |
| pyyaml                   | python       |     55 |   35 |  0 | 34 |  1 |
| pydantic                 | python       |     51 |   51 |  3 | 46 |  2 |
| pygments                 | python       |     63 |   37 |  2 | 16 | 19 |
| click                    | python       |     53 |   13 |  1 |  5 |  7 |
| numpy                    | python       |     24 |   24 |  2 | 20 |  2 |
| pycparser                | python       |     60 |    9 |  0 |  8 |  1 |
| anyio                    | python       |     47 |   16 |  4 | 10 |  2 |
| attrs                    | python       |     69 |   24 |  1 | 23 |  0 |
| h11                      | python       |     65 |   19 |  0 | 13 |  6 |
| fsspec                   | python       |     85 |   50 |  0 | 39 | 11 |
| pytest                   | python       |     57 |   33 |  4 | 26 |  3 |
| pandas                   | python       |     29 |   29 |  2 | 16 | 11 |
| httpx                    | python       |     81 |   26 |  0 | 25 |  1 |
| axios                    | javascript   |    300 |   14 |  7 |  3 |  4 |
| express                  | javascript   |    294 |   65 |  0 | 36 | 29 |
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
- **L1 — SSRF in dev tooling paths** (`SECURITY-046` in `scripts/`, `release/`, `ci/`, `.github/`, `conf.py`, `noxfile`, `Makefile`, etc.)
  - Rationale: `SECURITY-046` is a pattern-only SSRF rule (no taint tracking). It fires on any
    `requests.get(url)` with a variable URL. In release automation and doc builders this is
    developer-controlled code calling known endpoints — categorically not a web-app SSRF.
- **L2 — subprocess in build automation paths** (`SECURITY-022/026` in same non-runtime dirs)
  - Rationale: `B603/B607` are designed to catch web-app subprocess injection. In `setup.py`,
    `noxfile.py`, `scripts/` they fire on intentional `["git", "make"]` calls — not injection risks.

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
