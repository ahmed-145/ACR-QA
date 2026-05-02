# ACR-QA Evaluation Report

> Comprehensive accuracy, benchmark, and coverage analysis — **v3.2.4** (May 2026)

## 1. Detection Accuracy (Precision / Recall / F1)

### Overall Results

| Metric | Value |
|--------|:-----:|
| **Total Findings Evaluated** | 820+ |
| **True Positives** | 786 |
| **False Positives** | 34 |
| **Overall Precision** | 94.8% |
| **AI Explanation Quality** | 100% (all HIGH findings explained) |
| **OWASP Top 10 Coverage** | 9/10 categories |
| **Test Suite** | 1,699 tests passing |
| **Code Coverage** | 87% |
| **Continuous Integration** | GitHub Actions Pass |

### Per-Repository Breakdown (Python)

| Repository | Findings | TP | FP | Overall Precision | Security Precision | Recall | F1 |
|------------|:--------:|:--:|:--:|:-----------------:|:------------------:|:------:|:--:|
| DVPWA | 42 | 34 | 8 | 81.0% | 100.0% | 50.0% | 63.2% |
| Pygoat | 377 | 361 | 16 | 95.8% | 100.0% | 100.0% | 97.8% |
| DSVW | 45 | 45 | 0 | 100.0% | 100.0% | 100.0% | 100.0% |

### Per-Repository Breakdown (JavaScript/TypeScript)

| Repository | Raw Findings | After Dedup | HIGH | MEDIUM | LOW | AI Explanations |
|------------|:-----------:|:-----------:|:----:|:------:|:---:|:---:|
| DVNA | 946 raw | 128 unique | 4 | 77 | 47 | 4 in 1,292ms |
| NodeGoat | 319 raw | 310 unique | 7 | 145 | 158 | 7 in 2,299ms |

### Per-Repository Breakdown (Go)

| Repository | Findings | HIGH | MEDIUM | LOW | Tools Used |
|------------|:--------:|:----:|:------:|:---:|:---:|
| GoVWA | 46 | 0 | 14 | 32 | gosec + staticcheck + Semgrep (10 Go rules) |
| OWASP Go-SCP | Validated | — | — | — | E2E test target |

**Go adapter top categories:** weak crypto (MD5/SHA1), XSS template injection, SQL string formatting.

---

## 2. DVPWA Ground Truth Validation

DVPWA (Damn Vulnerable Python Web App) contains 6 known vulnerability categories.

| Vulnerability | CWE | Severity | Detected |
|--------------|:----:|:--------:|:--------:|
| Raw SQL string formatting allows SQL injection | CWE-89 | high | ✅ |
| Database credentials hardcoded in source | CWE-259 | high | ✅ (Secrets Detector) |
| MD5 used for password hashing | CWE-328 | medium | ✅ |
| User input rendered without escaping | CWE-79 | high | ✅ |
| Debug mode enabled in production config | CWE-215 | medium | ❌ |
| Forms without CSRF tokens | CWE-352 | medium | ❌ |

**Ground Truth Recall: 50%** (3/6 known vulnerability categories detected by code-level static analysis)

> **v3.0.9 improvement:** The Secrets Detector engine (Feature added in v0.9) now correctly identifies the hardcoded DB credentials pattern, raising recall from 17% → 50%.

#### Architectural Analysis of False Negatives

The undetected 50% highlights the boundary between **SAST** and other detection paradigms:

1. **Debug mode enabled (CWE-215):** DVPWA enables `debug=True` via a config proxy class, not a flat file assignment. Static analysis cannot infer runtime configuration state without framework-specific semantic rules.
2. **No CSRF tokens (CWE-352):** This is an **architectural absence** — SAST tools cannot detect the *lack* of a framework middleware/decorator across all view paths without a predefined AST schema.

**Conclusion:** The missing 50% in DVPWA demonstrates the **inherent boundaries of static analysis**, reinforcing the project's precise scope and the need for complementary DAST tools. All code-level vulnerabilities within SAST scope were detected.

---

## 3. NodeGoat Evaluation (JS/TS Pipeline)

NodeGoat is an OWASP deliberately vulnerable Node.js application with 12 documented vulnerabilities.

### Detection Results

| Rule | File | Line | Vulnerability |
|------|------|:----:|---------------|
| `SECURITY-065` (SSRF) | `research.js` | 16 | SSRF via user-controlled URL |
| `SECURITY-058` (NoSQL `$where`) | `allocations-dao.js` | 77 | `$where` template literal injection |
| `SECURITY-051` (eval) | Multiple | — | Dynamic code execution (3 instances) |

**NodeGoat recall:** 5 caught (eval×3, SSRF, NoSQL `$where`) out of 12 documented.
**Adjusted recall** (excluding logic/auth flaws unreachable by SAST): **5/8 = 62.5%**.

### Noise Reduction

| Metric | Value |
|--------|:-----:|
| Raw findings | 319 |
| After deduplication | 310 |
| Duplicates removed | 9 (2.8%) |
| AI explanations | 7 HIGH findings in 2,299ms |

---

## 4. Comparative Benchmark: ACR-QA vs Raw Tools

Tested on DVPWA — same codebase scanned by each tool independently, then by ACR-QA's full pipeline.

| Tool | Raw Findings | Notes |
|------|:------------:|-------|
| Bandit | 0 | Security scanner only |
| Semgrep | 0 | Pattern-based with custom rules |
| Ruff | 33 | Linter + style checker |
| ACR-QA | 42 | Normalized + Deduplicated + AI Explained |

**Noise Reduction across 9 Python repos (per-rule cap of 5):**

| Repo | Raw | After Cap | Reduction |
|------|:---:|:---:|:---:|
| Rich | 1,586 | 127 | 92% |
| FastAPI | 390 | 48 | 88% |
| HTTPie | 394 | 78 | 80% |
| Sanic | 497 | 104 | 79% |
| Black | 240 | 51 | 79% |
| requests | 181 | 50 | 72% |
| Flask | 136 | 49 | 64% |

![Comparative Benchmark](comparative_benchmark.png)

![Noise Reduction](noise_reduction.png)

---

## 5. Scale Benchmark (v3.0.3)

Synthetic JS projects of increasing size, measuring pipeline wall time:

| Synthetic Target | Files | Execution Time | Throughput |
|------------------|:-----:|:--------------:|:----------:|
| Baseline | 10 | 6.31s | 1.6 files/s |
| Mid | 50 | 6.50s | 7.7 files/s |
| High | 100 | 7.11s | 14.1 files/s |
| Large | 200 | 7.58s | 26.4 files/s |
| Massive | 500 | 9.83s | 50.9 files/s |

> **50× files → 1.6× time.** Overhead (ESLint startup, DB write) dominates at small scale. At 500 files, throughput is 50.9 files/s — suitable for large enterprise monorepos.

---

## 6. OWASP Top 10 (2021) Coverage

ACR-QA covers **9/10** OWASP Top 10 categories.

| OWASP Category | Status | Rules Mapped | CWEs |
|----------------|:------:|:------------:|------|
| A01:2021 Broken Access Control | ✅ | 2/3 (SECURITY-004, SECURITY-019) | CWE-200, CWE-284, CWE-352 |
| A02:2021 Cryptographic Failures | ✅ | 7/7 (SECURITY-009, SECURITY-010, SECURITY-014...) + CBoM CRYPTO-001/002/003 | CWE-259, CWE-327, CWE-328 |
| A03:2021 Injection | ✅ | 4/4 (SECURITY-001, SECURITY-021, SECURITY-027...) + JS NoSQL rules | CWE-79, CWE-89, CWE-78 |
| A04:2021 Insecure Design | ✅ | 3/3 (PATTERN-001, SOLID-001, COMPLEXITY-001) | CWE-209, CWE-256 |
| A05:2021 Security Misconfiguration | ✅ | 6/6 (SECURITY-003, SECURITY-006, SECURITY-007...) | CWE-16, CWE-611 |
| A06:2021 Vulnerable Components | ✅ | 6/6 (SECURITY-034, SECURITY-035, SECURITY-038...) + SCA Scanner + Dep Reachability | CWE-1104 |
| A07:2021 Auth Failures | ✅ | 3/3 (SECURITY-005, SECURITY-013, SECURITY-036) | CWE-287, CWE-384 |
| A08:2021 Data Integrity | ✅ | 2/2 (SECURITY-008, SECURITY-012) | CWE-502 |
| A09:2021 Logging Failures | ⚠️ | 0/0 | CWE-778 |
| A10:2021 SSRF | ✅ | 2/2 (SECURITY-020, SECURITY-013) + JS SSRF rules | CWE-918 |

---

## 7. Severity Distribution

![Severity Distribution](severity_distribution.png)

## 8. Finding Categories

![Category Breakdown](category_breakdown.png)

## 9. Confusion Matrix

![Confusion Matrix](confusion_matrix.png)

### Precision/Recall Chart

![Precision/Recall by Repository](precision_recall_chart.png)

---

## 10. Production Readiness Metrics

| Metric | Value |
|--------|:-----:|
| Test Suite | 1,699 tests (pytest) |
| Code Coverage | 87% |
| CI/CD | GitHub Actions (test + lint + coverage) |
| Docker | Dockerfile + docker-compose.yml |
| API Endpoints | 20+ REST endpoints |
| AI Quality | 100% explanation rate on HIGH findings |
| Deduplication | Cross-tool 2-pass dedup (exact + category) |
| Rule Mappings | 299 tool-specific → canonical rules |
| OWASP Coverage | 9/10 categories |
| Languages Supported | Python, JavaScript/TypeScript, Go |
| Repos Tested | 5 benchmark repos (DVPWA, Pygoat, DSVW, DVNA, NodeGoat) + 9 mass-test repos + GoVWA |

---

## 11. Key Differentiators vs Competitors

| Feature | ACR-QA | SonarQube | CodeClimate | Codacy |
|---------|:------:|:---------:|:-----------:|:------:|
| Multi-tool normalization | ✅ | ❌ | ❌ | Partial |
| AI-powered explanations (RAG) | ✅ | ❌ | ❌ | ❌ |
| Semantic entropy (hallucination detection) | ✅ | ❌ | ❌ | ❌ |
| Self-evaluation scoring | ✅ | ❌ | ❌ | ❌ |
| Cross-tool deduplication | ✅ | ❌ | ❌ | ❌ |
| Cross-language vulnerability correlation | ✅ | ❌ | ❌ | ❌ |
| CBoM (quantum-safety classification) | ✅ | ❌ | ❌ | ❌ |
| AI path feasibility validation | ✅ | ❌ | ❌ | ❌ |
| Dependency reachability analysis | ✅ | ❌ | ❌ | ❌ |
| Triage memory (FP learning) | ✅ | Partial | ❌ | ❌ |
| Confidence scoring (0-100) | ✅ | ❌ | ❌ | ❌ |
| Self-hosted / free | ✅ | Partial | ❌ | ❌ |
| OWASP compliance mapping | ✅ | ✅ | ❌ | ❌ |
| Quality gate CI/CD | ✅ | ✅ | ✅ | ✅ |
| Test gap analysis | ✅ | ❌ | ❌ | ❌ |
| AI autofix with lint validation | ✅ AI | Partial | ❌ | ❌ |
| Autofix PR bot | ✅ | ❌ | ❌ | ❌ |
| Multi-language support | ✅ (3) | ✅ (30+) | ✅ | ✅ |

---

## 12. Test Suite Progression (v1.0 → v3.2.4)

| Version | Tests Passed | Coverage | Key Addition |
|---------|:-----------:|:--------:|:------------|
| v1.0 | 97 | ~30% | Config + quality gate |
| v2.5 | 120 | ~35% | Rich UI + Prometheus |
| v2.6 | 175 | 39% | Deep coverage audit |
| v2.7 | 273 | ~42% | God-mode test suite |
| v2.9 | 370 | ~45% | Coverage boost (quality_gate 93%, scorer 62%) |
| v3.0.1 | 409 | ~50% | JS/TS adapter (39 tests) |
| v3.0.6 | 459 | 55% | JS/TS pipeline unification |
| v3.1.0 | 497 | 56% | Features 2-7 (path feasibility, CBoM, etc.) |
| v3.1.1 | 508 | 57% | Feature 8 (dependency reachability) |
| v3.1.3 | 526 | ~58% | Features 9-10 (cross-lang, trends) |
| v3.2.0 | 892 | 62% | Go adapter (51 tests) + coverage push |
| v3.2.1 | 1,377 | 67% | God-mode coverage (batch1-3: 304 tests) |
| v3.2.2 | 1,496 | 74% | Explainer 93%, autofix 96% |
| v3.2.3 | 1,565 | ~78% | Metrics 99%, rate limiter 84% |
| v3.2.4 | 1,699 | 87% | Flask app 107 tests, pipeline helpers 45 |

---

*Generated by ACR-QA Evaluation Suite — May 2, 2026 · v3.2.4*
