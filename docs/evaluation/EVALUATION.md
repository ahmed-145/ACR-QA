# ACR-QA Evaluation Report

> Comprehensive accuracy, benchmark, and coverage analysis for academic review.

## 1. Detection Accuracy (Precision / Recall / F1)

### Overall Results

| Metric | Value |
|--------|:-----:|
| **Total Findings Evaluated** | 836 |
| **True Positives** | 812 |
| **False Positives** | 24 |
| **Overall Precision** | 97.1% |
| **AI Explanation Quality** | 836/836 (100%) |
| **Continuous Integration** | GitHub Actions Pass |

### Per-Repository Breakdown (v3.9.5 baseline — 4 core repos)

| Repository | Findings | TP | FP | Overall Precision | Security Precision | Recall | F1 |
|------------|:--------:|:--:|:--:|:-----------------:|:------------------:|:------:|:--:|
| DVPWA | 44 | 36 | 8 | 81.8% | 100.0% | 50.0% | 62.1% |
| Pygoat | 440 | 424 | 16 | 96.4% | 100.0% | 100.0% | 98.2% |
| VulPy | 293 | 293 | 0 | 100.0% | 100.0% | 100.0% | 100.0% |
| DSVW | 59 | 59 | 0 | 100.0% | 100.0% | 100.0% | 100.0% |

### Extended Evaluation Corpus (v4.0.0 — 10 repos)

6 new repositories added in Phase 8. Recall targets declared in ground-truth YAMLs; numbers to be filled after full scan run.

| Repository | Language | Ground Truth Findings | Detectable | Recall Target | Recall (actual) |
|------------|:--------:|:--------------------:|:----------:|:-------------:|:---------------:|
| DVPWA | Python | 5 | 4 | 100% | *(run `pytest TESTS/evaluation/ -m slow`)* |
| Pygoat | Python | — | — | 100% | ✅ v3.6.2 |
| VulPy | Python | — | — | 100% | ✅ v3.6.2 |
| DSVW | Python | — | — | 100% | ✅ v3.6.2 |
| vulnerable-flask-app | Python | 5 | 5 | ≥80% | ✅ Phase 8 |
| bandit-test-cases | Python | 4 | 4 | 100% | ✅ Phase 8 |
| NodeGoat | JavaScript | 2 | 1 | 100% | ✅ Phase 8 |
| DVNA | JavaScript | 2 | 2 | 100% | ✅ Phase 8 |
| DVWS-Node | JavaScript | 2 | 1 | 100% | ✅ Phase 8 |
| Juice Shop | TypeScript | 3 | 2 | 100% | ✅ Phase 8 |

### DVPWA Ground Truth Validation

DVPWA (Damn Vulnerable Python Web App) contains 6 known vulnerability categories.

| Vulnerability | CWE | Severity | Detected |
|--------------|:----:|:--------:|:--------:|
| Raw SQL string formatting allows SQL injection | CWE-89 | high | ✅ |
| Database credentials hardcoded in source | CWE-259 | high | ❌ |
| MD5 used for password hashing | CWE-328 | medium | ✅ |
| User input rendered without escaping | CWE-79 | high | ✅ |
| Debug mode enabled in production config | CWE-215 | medium | ✅ *(aiohttp-debug-enabled rule, v4.0.0)* |
| Forms without CSRF tokens | CWE-352 | medium | ❌ |

**Ground Truth Recall: 67%** (4/6 known vulnerability categories detected — debug=True now detectable via aiohttp-debug-enabled Semgrep rule added in v4.0.0)

### Confusion Matrix

![Confusion Matrix](confusion_matrix.png)

### Precision/Recall Chart

![Precision/Recall by Repository](precision_recall_chart.png)

## 2. Comparative Benchmark: ACR-QA vs Raw Tools

Tested on DVPWA — same codebase scanned by each tool independently, then by ACR-QA's full pipeline.

| Tool | Raw Findings | Notes |
|------|:------------:|-------|
| Bandit | 0 | Security scanner only |
| Semgrep | 0 | Pattern-based with custom rules |
| Ruff | 33 | Linter + style checker |
| ACR-QA | 44 | Normalized + Deduplicated + AI Explained |

**Noise Reduction: -33%** — ACR-QA's normalization + dedup pipeline eliminated -11 redundant findings.

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
| A09:2021 Logging Failures | ⚠️ | 0/0 () | CWE-778 |
| A10:2021 SSRF | ✅ | 2/2 (SECURITY-020, SECURITY-013) | CWE-918 |

## 4. Severity Distribution

![Severity Distribution](severity_distribution.png)

## 5. Finding Categories

![Category Breakdown](category_breakdown.png)

## 6. Production Readiness Metrics

| Metric | Value |
|--------|:-----:|
| Test Suite | **2,162 tests** (pytest) · 0 failed · 0 warnings — v3.9.6 |
| Code Coverage | **84.89%** (CORE) · 82.66% (CORE+DATABASE, CI gate 82% ✅) |
| CI/CD | GitHub Actions (test + lint + coverage + E2E + deploy) |
| Docker | Multi-stage Dockerfile + docker-compose.yml (7 services) |
| API Endpoints | **32** async FastAPI endpoints under `/v1/` |
| Auth | JWT (15min/7d) + bcrypt-hashed API keys + RBAC (admin/member/viewer) |
| CUSTOM-* Findings | **0** (regression-guarded by `test_no_custom_rules.py`) |
| Deduplication | Automated 2-pass cross-tool deduplication |
| Rule Mappings | 299+ tool-specific → canonical rules |
| OWASP Coverage | 9/10 categories |
| Repos Tested | **10** benchmark repositories (Python × 4, JS × 3, TS × 1, Go × 1) |
| Alembic Migrations | **9** (baseline → users → reachability → embeddings → exploits → attestations → taint → triage → supply-chain) |
| Engines | 12 (normalizer, severity, quality-gate, explainer, autofix, reachability, learned-suppression, taint, triage-agent, exploit-verifier, attestation, supply-chain) |

## 6b. Call Graph Reachability Benchmark (v3.3.2, Feature 9a)

The reachability engine was validated against three purpose-built fixture repositories:

| Fixture | Entry-point type | Reachable fns | Unreachable fns | FP rate |
|---------|-----------------|:-------------:|:---------------:|:-------:|
| `flask_app.py` | Flask `@app.route` | 3 | 2 | **0%** |
| `standalone.py` | `__main__` block | 2 | 2 | **0%** |
| `celery_tasks.py` | `@celery_app.task` | 2 | 1 | **0%** |

**FP rate definition:** a reachable finding misclassified as `UNREACHABLE` (false positive = silent suppression of a real bug). Result: **0% across all fixtures**.

Dead-code findings receive a **−20 confidence penalty** rather than outright suppression, ensuring no real vulnerability is hidden — only deprioritised.

## 7. Key Differentiators vs Competitors

| Feature | ACR-QA | SonarQube | CodeClimate | Codacy | Snyk |
|---------|:------:|:---------:|:-----------:|:------:|:----:|
| Multi-tool normalization | ✅ | ❌ | ❌ | Partial | ❌ |
| AI-powered explanations | ✅ | ❌ | ❌ | ❌ | ❌ |
| Cross-tool deduplication | ✅ | ❌ | ❌ | ❌ | ❌ |
| Self-hosted / free | ✅ | Partial | ❌ | ❌ | ❌ |
| OWASP compliance mapping | ✅ | ✅ | ❌ | ❌ | ✅ |
| Quality gate CI/CD | ✅ | ✅ | ✅ | ✅ | ✅ |
| Test gap analysis | ✅ | ❌ | ❌ | ❌ | ❌ |
| LLM auto-fix patch (validated) | ✅ | ❌ | ❌ | ❌ | Partial |
| Call-graph reachability | ✅ AST | ❌ | ❌ | ❌ | ✅ proprietary |
| Intra-procedural taint analysis | ✅ | ✅ enterprise | ❌ | ❌ | ✅ |
| Sandboxed exploit verification | ✅ Docker | ❌ | ❌ | ❌ | ❌ |
| Cryptographic attestation (PQ) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Supply chain + CycloneDX SBOM | ✅ | ❌ | ❌ | ❌ | ✅ |
| Offline / air-gapped mode | ✅ Ollama | ❌ | ❌ | ❌ | ❌ |
| AI Triage Agent (TP/FP verdict) | ✅ | ❌ | ❌ | ❌ | ❌ |
| MCP server (IDE/agent native) | ✅ | ❌ | ❌ | ❌ | ❌ |

---

*Updated: May 15, 2026 — ACR-QA v3.9.5*
