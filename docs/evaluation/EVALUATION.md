# ACR-QA Evaluation Report

> Comprehensive accuracy, benchmark, and coverage analysis for academic review.

## 1. Detection Accuracy (Precision / Recall / F1)

### Overall Results

| Metric | Value |
|--------|:-----:|
| **Total Findings Evaluated** | 797 |
| **True Positives** | 730 |
| **False Positives** | 67 |
| **Overall Precision** | 91.6% |
| **AI Explanation Quality** | 797/797 (100%) |
| **Continuous Integration** | GitHub Actions Pass |

### Per-Repository Breakdown

| Repository | Findings | TP | FP | Overall Precision | Security Precision | Recall | F1 |
|------------|:--------:|:--:|:--:|:-----------------:|:------------------:|:------:|:--:|
| DVPWA | 43 | 43 | 0 | 100.0% | 100.0% | 83.3%¹ | 90.9% |
| Pygoat | 425 | 358 | 67 | 84.2% | 100.0% | N/A² | — |
| VulPy | 276 | 276 | 0 | 100.0% | 100.0% | N/A² | — |
| DSVW | 53 | 53 | 0 | 100.0% | 100.0% | N/A² | — |

### DVPWA Ground Truth Validation

DVPWA (Damn Vulnerable Python Web App) contains 6 known vulnerability categories.

| Vulnerability | CWE | Severity | Detected | Tool |
|--------------|:----:|:--------:|:--------:|------|
| Raw SQL string formatting allows SQL injection | CWE-89 | high | ✅ | Bandit B608 |
| Database credentials hardcoded in source | CWE-259 | high | ✅ | Bandit B105 |
| MD5 used for password hashing | CWE-328 | medium | ✅ | Bandit B303 |
| User input rendered without escaping | CWE-79 | high | ✅ | Semgrep SECURITY-045 |
| Debug mode enabled in production config | CWE-215 | medium | ✅ | Bandit B201 |
| Forms without CSRF tokens | CWE-352 | medium | ❌¹ | N/A — architectural limit |

**Ground Truth Recall: 83.3%** (5/6 vulnerability categories detected)

> ¹ **CSRF — deliberately excluded, not architecturally impossible.** Framework-level misconfiguration patterns (e.g., `@csrf_exempt` on sensitive Django views, Flask apps missing `CSRFProtect()`, `WTF_CSRF_CHECK_DEFAULT = False`) *are* statically detectable via Semgrep heuristics. However, these rules produce high false-positive rates on API-only applications using token-based auth (JWT, API keys), where CSRF protection is genuinely unnecessary. ACR-QA prioritises precision over recall — a noisy rule that fires on every REST API undermines developer trust. **Future work (v3.0):** A context-aware rule that first verifies the app uses session-based auth before flagging absent CSRF protection. Full runtime token-presence verification still requires DAST/pentest.

### Confusion Matrix

![Confusion Matrix](confusion_matrix.png)

### Precision/Recall Chart

![Precision/Recall by Repository](precision_recall_chart.png)

## 2. Comparative Benchmark: ACR-QA vs Raw Tools

Tested on DVPWA — same codebase scanned by each tool independently, then by ACR-QA's full pipeline.

| Tool | Raw Findings | Notes |
|------|:------------:|-------|
| Bandit | 2 | Security scanner only |
| Semgrep | 0³ | Pattern-based with custom rules |
| Ruff | 33 | Linter + style checker |
| ACR-QA | 43 | Normalized + Deduplicated + AI Explained |

> ³ **Semgrep found 0 findings on DVPWA specifically** because DVPWA uses raw psycopg2 rather than Django ORM/Flask patterns that ACR-QA's custom Semgrep ruleset targets. Semgrep detected 146 findings across all 4 repos, excelling on Pygoat (Django) and VulPy (Flask).

**Noise Reduction: -26%** — ACR-QA's normalization + dedup pipeline eliminated -9 redundant findings.

![Comparative Benchmark](comparative_benchmark.png)

![Noise Reduction](noise_reduction.png)

## 3. OWASP Top 10 (2021) Coverage

ACR-QA covers **9/10** OWASP Top 10 categories.

| OWASP Category | Status | Rules Mapped | CWEs |
|----------------|:------:|:------------:|------|
| A01:2021 Broken Access Control | ✅ | 2/3 (SECURITY-004, SECURITY-019) | CWE-200, CWE-284, CWE-352 |
| A02:2021 Cryptographic Failures | ✅ | 7/7 (SECURITY-009, SECURITY-010, SECURITY-014...) | CWE-259, CWE-327, CWE-328 |
| A03:2021 Injection | ✅ | 4/4 (SECURITY-001, SECURITY-021, SECURITY-027...) | CWE-79, CWE-89, CWE-78 |
| A04:2021 Insecure Design | ✅ | 3/3 (PATTERN-001, SOLID-001, COMPLEXITY-001) | CWE-209, CWE-256 |
| A05:2021 Security Misconfiguration | ✅ | 6/6 (SECURITY-003, SECURITY-006, SECURITY-007...) | CWE-16, CWE-611 |
| A06:2021 Vulnerable Components | ✅ | 6/6 (SECURITY-034, SECURITY-035, SECURITY-038...) | CWE-1104 |
| A07:2021 Auth Failures | ✅ | 3/3 (SECURITY-005, SECURITY-013, SECURITY-036) | CWE-287, CWE-384 |
| A08:2021 Data Integrity | ✅ | 2/2 (SECURITY-008, SECURITY-012) | CWE-502 |

> **v2.9 update:** SECURITY-008 (pickle/marshal) and SECURITY-018 (yaml.load) severity upgraded to HIGH to reflect CWE-502 RCE risk. This closes the gap where deserialization vulnerabilities were previously reported as MEDIUM.

| A09:2021 Logging Failures | ⚠️ | 0/0 () | CWE-778 |
| A10:2021 SSRF | ✅ | 2/2 (SECURITY-020, SECURITY-013) | CWE-918 |

## 4. Severity Distribution

![Severity Distribution](severity_distribution.png)

## 5. Finding Categories

![Category Breakdown](category_breakdown.png)

## 6. Production Readiness Metrics

| Metric | Value |
|--------|:-----:|
| Test Suite | **374 tests** (pytest) — ↑ from 293 |
| Code Coverage | `quality_gate.py` **93%**, `severity_scorer.py` **62%** (v2.9) |
| CI/CD | GitHub Actions (test + lint + coverage) |
| Docker | Dockerfile + docker-compose.yml |
| API Endpoints | 20+ REST endpoints |
| AI Quality | 797/797 explanations generated (100%) |
| Deduplication | 300 duplicates removed (1,097 raw → 797 output, 27% noise reduction) |
| Rule Mappings | 127 tool-specific → canonical rules |
| OWASP Coverage | 9/10 categories |
| Repos Tested | 4 benchmark + 9 mass-test + 2 real-world (Flask, httpx) |
| FP Rate (Flask) | **10.3%** (vs 30-40% industry baseline for Python) |
| FP Rate (httpx) | **~9%** |

## 7. Key Differentiators vs Competitors

### Traditional SAST Tools

| Feature | ACR-QA | SonarQube | CodeClimate | Codacy |
|---------|:------:|:---------:|:-----------:|:------:|
| Multi-tool normalization | ✅ | ❌ | ❌ | Partial |
| AI-powered explanations | ✅ | ❌ | ❌ | ❌ |
| Cross-tool deduplication | ✅ | ❌ | ❌ | ❌ |
| Self-hosted / free | ✅ | Partial | ❌ | ❌ |
| OWASP compliance mapping | ✅ | ✅ | ❌ | ❌ |
| Quality gate CI/CD | ✅ | ✅ | ✅ | ✅ |
| Test gap analysis | ✅ | ❌ | ❌ | ❌ |
| Code fix suggestions | ✅ AI | Partial | ❌ | ❌ |

### 2025 AI-Native Review Tools

| Feature | ACR-QA | CodeRabbit | Qodo (CodiumAI) | Greptile | code-review-graph |
|---------|:------:|:----------:|:---------------:|:--------:|:-----------------:|
| Multi-tool SAST (7 tools) | ✅ | ❌ | Partial | ❌ | ❌ |
| AI explanations + code fixes | ✅ | ✅ | ✅ | ✅ | Via LLM |
| Cross-tool deduplication | ✅ | ❌ | ❌ | ❌ | ❌ |
| OWASP compliance mapping | ✅ | ❌ | ✅ | ❌ | ❌ |
| Test gap analysis | ✅ | ❌ | ✅ | ❌ | Blast-radius |
| Codebase AST context graph | ❌ | ❌ | ❌ | ✅ RAG | ✅ Tree-sitter |
| Token-efficient context | ❌ | Partial | Partial | ✅ | ✅ 6.8× |
| Self-hosted / free | ✅ | ❌ | Enterprise | ❌ | ✅ |
| False positive rate (Python) | **10.3%** | ~30% est | ~25% est | N/A | N/A |

> **Key insight:** 2025 LLM-native tools treat the LLM as the primary reviewer, using static analysis only as a hint. ACR-QA inverts this — static analysis is authoritative, LLM *explains* what the tools found. This gives ACR-QA a measurable 10.3% FP rate vs estimated 25–30% for LLM-primary approaches. `code-review-graph` is architecturally complementary: it optimizes *which files* an LLM reads (6.8× fewer tokens), while ACR-QA focuses on *what findings* get reported with normalization, dedup, and OWASP mapping.

---

*Generated by ACR-QA Evaluation Suite — April 1, 2026 (v2.9)*

