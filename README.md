<div align="center">

# 🛡️ ACR-QA
### Automated Code Review & Quality Assurance Platform

*Intelligent, context-aware code analysis with RAG-enhanced AI explanations*

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![CI Tests](https://github.com/ahmed-145/ACR-QA/actions/workflows/tests.yml/badge.svg)](https://github.com/ahmed-145/ACR-QA/actions/workflows/tests.yml)
[![Tests](https://img.shields.io/badge/Tests-1496%20passing-22c55e?logo=pytest&logoColor=white)](./TESTS/)
[![Version](https://img.shields.io/badge/Version-3.2.0-blue)](CHANGELOG.md)
[![PostgreSQL 15](https://img.shields.io/badge/PostgreSQL-15+-336791?logo=postgresql&logoColor=white)](https://postgresql.org/)
[![Prometheus](https://img.shields.io/badge/Prometheus-monitored-e6522c?logo=prometheus&logoColor=white)](https://prometheus.io/)
[![Rules](https://img.shields.io/badge/Rules-299%20mapped-8b5cf6?logo=shield&logoColor=white)](./docs/evaluation/PER_TOOL_EVALUATION.md)
[![Languages](https://img.shields.io/badge/Languages-Python%20%7C%20JS%20%7C%20TS%20%7C%20Go-00ADD8?logo=go&logoColor=white)](./CORE/adapters/)
[![Precision](https://img.shields.io/badge/Precision-100%25-22c55e?logo=target&logoColor=white)](./docs/evaluation/PER_TOOL_EVALUATION.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[Quick Start](#-quick-start) · [Features](#-features) · [Architecture](#-architecture) · [CLI](#-cli-reference) · [CI/CD](#-cicd-integration) · [Monitoring](#-monitoring) · [Docs](#-documentation)

</div>

---

## 🎯 What is ACR-QA?

ACR-QA is a **provenance-first, AI-augmented code review platform**. It runs **7 static analysis tools** in parallel, normalizes every finding into a canonical schema, and generates evidence-grounded explanations using Retrieval-Augmented Generation (RAG) — all at **zero recurring cost** (free-tier Cerebras API).

**Key differentiators vs SonarQube / CodeRabbit:**
- 🧠 **RAG-grounded explanations** — 66-rule knowledge base with source citations, not generic AI
- 🎯 **Hallucination detection** — semantic entropy scoring (runs LLM 3× and measures consistency)
- 💰 **Cost-benefit analysis** — calculates ROI per finding (no competitor does this)
- 🔐 **Full provenance** — every LLM prompt and response is stored and auditable
- 💵 **$0 recurring cost** — uses free-tier APIs only
- 🧪 **Test Gap Analyzer** — AST-based detection of untested functions/classes (no competitor does this)
- 📋 **OWASP Compliance Reports** — maps findings to OWASP Top 10 + CWE IDs
- 🔇 **Confidence-based noise control** — filter low-confidence findings (`?min_confidence=0.7`)
- 📜 **Policy-as-Code Engine** — `.acrqa.yml` with schema validation, programmatic inspection, and documented templates

---

## ✨ Features

### 🔍 Multi-Tool Detection Pipeline

| Tool | What It Catches | Output |
|------|----------------|--------|
| **Ruff** | Style, imports, unused code, PEP8 | JSON |
| **Semgrep** | Security patterns (OWASP Top 10), custom rules | JSON |
| **Bandit** | Python security vulnerabilities (33 rules mapped) | JSON |
| **Vulture** | Dead code, unreachable branches | Text |
| **Radon** | Cyclomatic complexity, maintainability index | JSON |
| **Secrets Detector** | API keys, passwords, JWTs, tokens, private keys | Custom |
| **SCA Scanner** | Known-vulnerable dependency versions | Custom |
| **ESLint** | JavaScript/TypeScript security rules | JSON |
| **gosec** | Go security vulnerabilities | JSON |
| **staticcheck** | Go static analysis and bug detection | Text |

- **Cryptographic Bill of Materials (CBoM)** — inventories all cryptographic API usage across Python and JS/TS, classifies every algorithm by quantum-safety status per NIST FIPS 203/204 (2024 PQC standards), and flags non-quantum-safe algorithms (MD5, SHA1, RSA, ECDSA, DES) with post-quantum replacements (ML-KEM, ML-DSA, SHA3, BLAKE2)

- **Cross-Language Vulnerability Correlator** (Feature 9) — detects vulnerability chains spanning Python backend, Jinja2/HTML templates, and JS frontend in the same project. Inspired by CHARON (CISPA/NDSS). Detects `SQLI_TO_TEMPLATE`, `TEMPLATE_INJECTION`, `XSS_CHAIN`, and `ROUTE_JS_CHAIN` correlation types with confidence boosts (+10 to +20).

All outputs are normalized into a **canonical schema** → deduplicated → severity-scored → stored in PostgreSQL.

### 🧠 AI Explanations (RAG-Enhanced)

| Feature | How It Works |
|---------|-------------|
| **66-rule knowledge base** | Every normalizer rule has a `rules.yml` entry with rationale, remediation, and code examples (100% coverage) |
| **Evidence-grounded prompts** | LLM never explains a rule it can't cite — no hallucination by design |
| **Semantic entropy** | Runs LLM 3× with different temperatures, measures response consistency (0–1 score) |
| **Self-evaluation** | LLM rates its own output on relevance / accuracy / clarity (1–5) |
| **Confidence badges** | 🎯 Color-coded (High/Medium/Low) per finding on the dashboard |

### 🔧 Auto-Fix Engine

- Generates **before/after code diffs** for 8 fixable rule categories
- Per-rule **confidence scores** (60–95%)
- **Fix verification** — re-runs Ruff on the patched code to confirm the fix
- Activated via `--auto-fix` flag or auto-applies fixes above configurable confidence threshold

### 🚦 Quality Gates

Configurable severity thresholds that **fail CI with exit code 1** when exceeded (in `block` mode).

```yaml
# .acrqa.yml
quality_gate:
  mode: block        # block = fail CI + prevent merge | warn = post PR comment but allow merge
  max_high: 0        # Zero tolerance for high-severity
  max_medium: 5      # Allow up to 5 medium issues
  max_total: 50      # Cap total findings
  max_security: 0    # Zero tolerance for security issues
```

### ⚙️ Per-Repo Configuration (`.acrqa.yml`)

Drop a `.acrqa.yml` in any repo to customize:
- **Enable/disable rules** — `disabled_rules: [IMPORT-001, VAR-001]`
- **Override severity** — `severity_overrides: {STYLE-001: low}`
- **Ignore paths** — `ignore_paths: [__pycache__, .venv, node_modules]`
- **AI settings** — max explanations, model selection, confidence thresholds
- **Quality gate thresholds** — per-repo pass/fail criteria

### 🛑 Inline Suppression

```python
result = eval(user_input)  # acr-qa:ignore
password = "secret123"     # acrqa:disable SECURITY-005
```

### 📊 Web Dashboard

Access at **http://localhost:5000** — modern dark-mode UI:

| Feature | Description |
|---------|-------------|
| Severity counters | 🔴 High / 🟡 Medium / 🟢 Low with live counts |
| 💰 Cost-benefit widget | Analysis cost, hours saved, ROI ratio, cost-per-finding |
| Trend charts | Per-run severity breakdown over last 30 runs |
| Finding cards | Collapsible with AI explanation, code snippet, 🎯 confidence badge |
| False-positive feedback | 👍/👎 buttons on every finding for continuous improvement |
| Filters | By severity, category, rule ID, and full-text search |
| Export | SARIF, provenance trace, Markdown reports |

### 🖥️ Rich Terminal UI

Use the `--rich` flag for beautiful color-coded output:

```bash
python3 CORE/main.py --target-dir ./myproject --rich
```

Displays severity-colored findings table + quality gate panel with Rich library.

### 🔒 Security & Compliance

- **OWASP Top 10 Compliance Report** — maps all security findings to OWASP (2021) categories with CWE IDs (`/api/runs/{id}/compliance`)
- **SARIF v2.1.0** export → GitHub Security tab integration
- **Full provenance** — every LLM call stored with prompt, response, latency, model
- **Non-root Docker** — container runs as `acrqa` user with health checks
- **Rate limiting** — Redis-backed, 1 analysis per repo per minute
- **Confidence-based noise control** — `?min_confidence=0.7` filter suppresses low-quality findings
- **Feedback-driven severity tuner** — auto-generates severity overrides from false-positive feedback

### 🧪 Test Gap Analyzer

AST-based detection of untested functions and classes — **no competitor offers this**:

```bash
python3 scripts/test_gap_analyzer.py --target CORE/ --format text
```

- Parses source files with Python AST to extract all public functions/classes
- Discovers test files and maps tested symbols via naming conventions + import analysis
- Priority-ranks untested symbols by cyclomatic complexity
- Integrates with quality gate (fails CI if too many complex symbols are untested)
- API endpoint: `GET /api/test-gaps`

### 📜 Policy-as-Code Engine

`.acrqa.yml` is a full policy definition — not just config:

```bash
# Validate your policy
python3 scripts/validate_config.py --validate

# Generate documented template
python3 scripts/validate_config.py --generate-template > .acrqa.yml

# Inspect active policy via API
curl http://localhost:5000/api/policy
```

See [Policy Engine Documentation](docs/POLICY_ENGINE.md) for full reference.

---

## 🚀 Quick Start

### Option A — Docker (Recommended)

```bash
# 1. Clone
git clone https://github.com/ahmed-145/acr-qa.git && cd acr-qa

# 2. Configure
cp .env.example .env          # add your CEREBRAS_API_KEY

# 3. Start everything
make up
```

| Service | URL | Purpose |
|---------|-----|---------|
| 📊 Dashboard | http://localhost:5000 | Web UI + REST API |
| 📈 Grafana | http://localhost:3000 | Monitoring (admin/admin) |
| 🔥 Prometheus | http://localhost:9090 | Metrics scraping |
| 🗄️ PostgreSQL | localhost:5433 | Provenance database |
| 🔴 Redis | localhost:6379 | Rate limiting & caching |

### Option B — Local (no Docker)

```bash
# Prerequisites: Python 3.11+, PostgreSQL 15+
pip install -r requirements.txt
pip install ruff semgrep vulture radon bandit
npm install -g jscpd

createdb acrqa
psql -d acrqa -f DATABASE/schema.sql

cp .env.example .env   # fill in CEREBRAS_API_KEY
source .env
python3 FRONTEND/app.py   # → http://localhost:5000
```

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        ACR-QA v3.0 Pipeline                         │
│                                                                      │
│  GitHub PR ──► Detection Layer ──► Normalizer ──► Severity Scorer   │
│                ┌─────────────┐     ┌──────────┐   ┌──────────────┐  │
│                │ Ruff        │     │ Canonical │   │ Config-aware │  │
│                │ Semgrep     │────►│ Schema    │──►│ Dedup + Gate │  │
│                │ Bandit      │     │ (Finding) │   │ (.acrqa.yml) │  │
│                │ Vulture     │     └──────────┘   └──────┬───────┘  │
│                │ Radon       │                           │          │
│                │ Secrets     │                           ▼          │
│                │ SCA         │            ┌─────────────────────┐   │
│                │ gosec       │            │   RAG Explainer     │   │
│                │ staticcheck │            │   66 rules.yml KB   │   │
│                │ ESLint      │            │   Cerebras LLM      │   │
│                └─────────────┘            │   + Entropy (3×)    │   │
│                                           │   + Self-eval       │   │
│                                           └──────────┬──────────┘   │
│                                                     │              │
│              ┌───────────┐                          ▼              │
│              │ Dashboard │◄────── PostgreSQL ◄─────────────────────│
│              │ /metrics  │        (provenance)                     │
│              │ PR Comment│──────► GitHub / GitLab API               │
│              │ Rich CLI  │                                         │
│              └───────────┘                                         │
└──────────────────────────────────────────────────────────────────────┘
```

### Project Structure

```
acr-qa/
├── CORE/
│   ├── main.py                  # Analysis pipeline orchestrator
│   ├── config_loader.py         # .acrqa.yml parser + defaults
│   ├── engines/
│   │   ├── normalizer.py        # 71 tool rules → canonical schema
│   │   ├── severity_scorer.py   # Context-aware severity assignment
│   │   ├── quality_gate.py      # Configurable pass/fail thresholds
│   │   ├── explainer.py         # RAG + LLM + entropy + self-eval
│   │   ├── autofix.py           # Code fix generation + verification
│   │   ├── secrets_detector.py  # API key / credential detection
│   │   ├── sca_scanner.py       # Dependency vulnerability scanning
│   │   └── ai_code_detector.py  # AI-generated code detection
│   └── utils/
│       ├── code_extractor.py    # Source code context extraction
│       ├── metrics.py           # Prometheus counters & histograms
│       └── rate_limiter.py      # Redis-backed rate limiting
├── DATABASE/
│   ├── schema.sql               # PostgreSQL schema (5 tables, idempotent)
│   └── database.py              # DB interface with reconnection logic
├── FRONTEND/
│   ├── app.py                   # Flask dashboard + REST API + /metrics
│   └── templates/index.html     # Dark-mode responsive UI
├── TOOLS/
│   ├── run_checks.sh            # Parallel tool execution
│   └── semgrep/                 # Custom Semgrep security rules
│       ├── python-rules.yml
│       ├── js-rules.yml
│       └── go-rules.yml
├── scripts/
│   ├── post_pr_comments.py      # GitHub PR comment poster
│   ├── post_gitlab_comments.py  # GitLab MR comment poster
│   ├── export_sarif.py          # SARIF v2.1.0 export
│   ├── export_provenance.py     # Full audit trail export
│   ├── generate_report.py       # Markdown report generator
│   ├── generate_pr_summary.py   # PR summary generator
│   ├── generate_compliance_report.py  # OWASP Top 10 compliance (v2.7)
│   ├── test_gap_analyzer.py     # AST-based test gap analysis (v2.7)
│   ├── feedback_tuner.py        # Feedback-driven severity tuner (v2.7)
│   ├── validate_config.py       # Policy validator + template generator (v2.7)
│   ├── simulate_traffic.py      # Traffic simulator for Grafana metrics
│   ├── compute_metrics.py       # Precision/recall evaluation
│   ├── create_fix_pr.py         # Auto-fix PR creation via GitHub API
│   └── user_study.py            # User study tooling
├── config/
│   ├── rules.yml                # 66-rule RAG knowledge base
│   ├── prometheus.yml           # Prometheus scrape config
│   └── grafana/                 # Grafana auto-provisioning
│       ├── provisioning/        # Datasource + dashboard providers
│       └── dashboards/          # Pre-built dashboard (6 panels)
├── TESTS/                       # 275-test pytest suite
│   ├── test_acceptance.py       # Pipeline E2E tests
│   ├── test_api.py              # All Flask API endpoints
│   ├── test_explainer.py        # RAG + LLM integration
│   ├── test_normalizer.py       # Multi-tool normalization
│   ├── test_new_engines.py      # Secrets, SCA, autofix, confidence scorer (Feature 5)
│   ├── test_config_quality.py   # ConfigLoader + QualityGate
│   ├── test_pydantic_validation.py  # Schema validation
│   ├── test_rate_limiting.py    # Redis rate limiter
│   ├── test_deep_coverage.py    # 98 deep-coverage tests (v2.6)
│   ├── test_god_mode.py         # 78 god-mode tests — all features (v2.7)
│   └── test_integration_benchmarks.py  # Performance
├── .github/workflows/
│   ├── acr-qa.yml               # PR analysis workflow
│   └── tests.yml                # Internal test workflow
├── .gitlab-ci.yml               # GitLab CI pipeline
├── docker-compose.yml           # Full stack deployment
├── Dockerfile                   # Non-root, health-checked image
├── Makefile                     # One-command operations
└── .acrqa.yml                   # Default project config
```

---

## 💻 CLI Reference

```bash
python3 CORE/main.py [options]

Options:
  --target-dir DIR     Directory to analyze (default: samples/realistic-issues)
  --repo-name NAME     Repository name for provenance tracking
  --pr-number N        PR number (enables PR comment posting)
  --limit N            Max findings to explain (default: 50)
  --diff-only          Analyze only files changed in git diff
  --diff-base BRANCH   Base branch for diff (default: main)
  --auto-fix           Generate auto-fix suggestions for fixable rules
  --rich               Beautiful terminal output with Rich tables & panels
  --lang LANG          Language: auto (default) | python | javascript | typescript | go
  --no-ai              Skip AI explanation step (faster, no API key needed)
  --json               Output findings as JSON (pipe-friendly)
  --version            Print ACR-QA version and exit
```

### Examples

```bash
# Analyze a Python project
python3 CORE/main.py --target-dir ./myproject --limit 100

# Analyze a JavaScript / TypeScript project
python3 CORE/main.py --target-dir ./my-react-app --lang javascript --no-ai

# Auto-detect language (checks for package.json, .py, .ts files)
python3 CORE/main.py --target-dir ./myproject

# JSON output for scripting / CI pipelines
python3 CORE/main.py --target-dir . --json --no-ai > findings.json

# PR diff mode (only changed files)
python3 CORE/main.py --target-dir . --diff-only --diff-base main

# Auto-fix with Rich output
python3 CORE/main.py --target-dir . --auto-fix --rich

# Export SARIF for GitHub Security tab
python3 scripts/export_sarif.py --run-id <RUN_ID> --output findings.sarif

# Generate Markdown report
python3 scripts/generate_report.py <RUN_ID>

# View full provenance trace
python3 scripts/export_provenance.py <RUN_ID>

# Generate default .acrqa.yml config
make init-config
```

---

## 🟨 JavaScript / TypeScript Support (Verified)

ACR-QA v3.0.8 ships with a **full JS/TS language adapter** — no configuration required.

### How It Works

```
JS/TS Project
    │
    ├── ESLint (eslint-plugin-security)   → 20 rules: no-eval, object-injection, unsafe-regex…
    ├── Semgrep (TOOLS/semgrep/js-rules.yml) → 15 custom rules: XSS, SQLi, prototype pollution…
    └── npm audit                          → CVE dependency scan → SECURITY-059/SECURITY-060
         │
         ▼
    Normalizer → 56 rule mappings → CanonicalFinding (same schema as Python)
         │
         ▼
    Severity Scorer + Quality Gate + AI Explanations
```

### Usage

```bash
# Auto-detect (ACR-QA checks for package.json + .js/.ts files automatically)
python3 CORE/main.py --target-dir ./my-react-app

# Force JS mode
python3 CORE/main.py --target-dir ./my-express-api --lang javascript --no-ai

# TypeScript project
python3 CORE/main.py --target-dir ./my-next-app --lang typescript

# JSON output — pipe into jq or any CI tool
python3 CORE/main.py --target-dir . --lang javascript --json --no-ai | jq '.findings[] | select(.severity == "high")'
```

### Security Rules Covered (JS/TS)

| Threat | Tool | Canonical ID | Severity |
|--------|------|-------------|---------|
| eval() / new Function() injection | ESLint + Semgrep | SECURITY-001 | 🔴 HIGH |
| SQL injection (string concat) | Semgrep | SECURITY-027 | 🔴 HIGH |
| NoSQL injection (MongoDB) | Semgrep | SECURITY-058 | 🔴 HIGH |
| XSS (innerHTML, document.write) | Semgrep | SECURITY-045 | 🔴 HIGH |
| Prototype pollution | Semgrep | SECURITY-057 | 🔴 HIGH |
| Path traversal (req.params) | Semgrep | SECURITY-049 | 🔴 HIGH |
| Command injection (exec/spawn) | Semgrep | SECURITY-021 | 🔴 HIGH |
| Hardcoded secrets | Semgrep | SECURITY-005 | 🔴 HIGH |
| JWT none algorithm | Semgrep | SECURITY-047 | 🔴 HIGH |
| Dynamic require() | ESLint | SECURITY-052 | 🔴 HIGH |
| Object injection | ESLint | SECURITY-056 | 🔴 HIGH |
| ReDoS (unsafe regex) | ESLint | SECURITY-051 | 🔴 HIGH |
| npm CVE (critical/high) | npm audit | SECURITY-059 | 🔴 HIGH |
| Math.random() (weak crypto) | Semgrep | SECURITY-037 | 🟡 MEDIUM |
| npm CVE (moderate) | npm audit | SECURITY-060 | 🟡 MEDIUM |

### Prerequisites (JS mode)

```bash
npm install -g eslint eslint-plugin-security   # ESLint security plugin
# semgrep  ← already installed system-wide
# npm      ← already installed with Node.js
```

---

## 🟦 Go Support (Verified)

ACR-QA v3.2.0 ships with a **full Go language adapter** — no configuration required.

### How It Works

```text
Go Project
    │
    ├── gosec                             → Official Go security scanner (JSON output)
    ├── staticcheck                       → Advanced static analysis (Text output)
    └── Semgrep (TOOLS/semgrep/go-rules.yml) → Custom rules: Goroutine leaks, defer in loop, logic bugs...
         │
         ▼
    Normalizer → Rule mappings + dynamic line range handling → CanonicalFinding
         │
         ▼
    Severity Scorer + Quality Gate + AI Explanations
```

### Usage

```bash
# Auto-detect (ACR-QA checks for go.mod + .go files automatically)
python3 CORE/main.py --target-dir ./my-go-api

# Force Go mode
python3 CORE/main.py --target-dir ./my-go-cli --lang go
```

### Prerequisites (Go mode)

```bash
# Ensure gosec and staticcheck are installed and in your PATH
go install github.com/securego/gosec/v2/cmd/gosec@latest
go install honnef.co/go/tools/cmd/staticcheck@latest
```

---

## 🔗 CI/CD Integration

### GitHub Actions (Automatic)

The `.github/workflows/acr-qa.yml` workflow triggers on every PR:

1. Checks out PR diff
2. Runs all 7 analysis tools on changed files (`--diff-only`)
3. Normalizes, scores, and generates AI explanations
4. Posts severity-sorted comments on the PR
5. Enforces quality gate — **blocks merge** if thresholds exceeded

**Required secrets** (repo Settings → Secrets):
```
CEREBRAS_API_KEY   # For AI explanations
GITHUB_TOKEN       # Automatically provided by Actions
```

### Manual Trigger

Comment on any PR:
```
acr-qa review
```
The bot reacts with 👀 → runs analysis → posts results → reacts with 🚀.

### GitLab CI

`.gitlab-ci.yml` provides equivalent functionality. Set `CEREBRAS_API_KEY` and `GITLAB_TOKEN` in CI/CD Variables.

---

## 📈 Monitoring

### Prometheus `/metrics`

ACR-QA exposes a Prometheus-compatible `/metrics` endpoint. Docker auto-scrapes every 15s.

```
acrqa_http_requests_total{endpoint, method, status_code}
acrqa_http_request_duration_seconds{endpoint}
acrqa_http_errors_total{endpoint}
```

### Grafana Dashboards

Pre-built dashboard with **6 panels** at **http://localhost:3000** (admin/admin):

| Panel | Query |
|-------|-------|
| 🌐 Request Rate | `rate(acrqa_http_requests_total[5m])` |
| ⏱️ Response Time P95/P50 | `histogram_quantile(0.95, ...)` |
| 📊 Total Requests | `sum(acrqa_http_requests_total)` |
| ✅ HTTP Success Rate | `2xx / total * 100` |
| 🧠 LLM Latency | `avg(explain endpoint duration)` |
| 🔴 Error Rate | `rate(5xx responses[1m])` |

---

## 🧪 Testing

```bash
make test-all          # Full pytest suite (526 tests)
make test              # Acceptance tests only
make run               # Run analysis on sample files
make test-e2e          # End-to-end with Docker
```

**526 tests passing**, 4 skipped (infrastructure-dependent):

| Test File | # | Coverage |
|-----------|:-:|----------|
| `test_acceptance.py` | 4 | Pipeline E2E with mocked LLM |
| `test_api.py` | 9 | All Flask API endpoints |
| `test_explainer.py` | 9 | RAG + entropy + self-eval |
| `test_normalizer.py` | 7 | Ruff / Bandit / Semgrep normalization |
| `test_new_engines.py` | 56 | Secrets, SCA, autofix, CBoM, quality gate, Feature 4 & 5 |
| `test_config_quality.py` | 23 | ConfigLoader + QualityGate |
| `test_pydantic_validation.py` | 8 | Canonical schema validation |
| `test_rate_limiting.py` | 8 | Redis rate limiter (token bucket) |
| `test_deep_coverage.py` | 100 | 12-module deep coverage (v2.6) |
| `test_god_mode.py` | 84 | All new features + regression + edge cases |
| `test_integration_benchmarks.py` | 15 | Performance benchmarks |
| `test_js_adapter.py` | 63 | JS/TS adapter, E2E pipeline, CLI routing |
| `test_go_adapter.py` | 51 | Go adapter, tools extraction, semgrep local rules |
| `test_coverage_boost.py` | 77 | quality_gate + severity_scorer paths |
| `test_user_study.py` | 18 | User study module |

---

## 🔬 Thesis Evaluation

### Research Questions

| RQ | Question | Implementation | Metric |
|----|----------|----------------|--------|
| RQ1 | Can RAG reduce LLM hallucination? | 66-rule `rules.yml` KB + evidence-grounded prompts + entropy | `consistency_score` (0–1) |
| RQ2 | How to ensure provenance? | Full PostgreSQL audit trail per LLM call | `llm_explanations` table |
| RQ3 | What confidence scoring works? | Per-finding score: rule citation × entropy × self-eval | `confidence_score` + `self_eval_score` |
| RQ4 | Does it match industry tools? | 7-tool pipeline vs CodeRabbit / SonarQube | Feature parity table ↓ |

### Industry Feature Parity

| Feature | CodeRabbit | SonarQube | ACR-QA |
|---------|:----------:|:---------:|:------:|
| Multi-tool analysis | ✅ | ✅ | ✅ 7 tools |
| AI explanations | ✅ | ✅ | ✅ RAG + entropy |
| Source citations | ✅ | ✅ | ✅ rule ID links |
| Auto-fix suggestions | ✅ | ✅ | ✅ with verification |
| Quality gates | ✅ | ✅ | ✅ configurable |
| Inline suppression | ✅ | ✅ | ✅ `# acr-qa:ignore` |
| Per-repo config | ✅ | ✅ | ✅ `.acrqa.yml` |
| Finding dedup | ✅ | ✅ | ✅ tool-priority |
| GitHub CI/CD | ✅ | ✅ | ✅ |
| GitLab CI/CD | ✅ | ✅ | ✅ |
| SARIF export | ✅ | ✅ | ✅ v2.1.0 |
| OWASP compliance report | ✅ | ✅ | ✅ with CWE mapping |
| Secrets detection | ✅ | ✅ | ✅ |
| SCA scanning | ✅ | ✅ | ✅ |
| Rich terminal UI | ❌ | ❌ | ✅ |
| Cost-benefit analysis | ❌ | ❌ | ✅ |
| Hallucination detection | ❌ | ❌ | ✅ entropy |
| **Test gap analysis** | ❌ | ❌ | ✅ AST-based |
| **Confidence-based filtering** | ❌ | ❌ | ✅ per-finding |
| **Feedback-driven tuning** | ❌ | ❌ | ✅ auto-overrides |
| **Policy-as-code engine** | ❌ | ✅ | ✅ with validator |
| **Config validator** | ❌ | ❌ | ✅ schema + templates |
| Recurring cost | $$$ | $$$ | **$0** |

---

## 🛠️ Technology Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| Web Framework | Flask 3.x |
| Database | PostgreSQL 15 |
| Cache / Rate Limiting | Redis 7 |
| AI Model | Cerebras Llama 3.1 8B (free tier) |
| Static Analysis | Ruff, Semgrep, Bandit, Vulture, Radon |
| Terminal UI | Rich |
| Containerization | Docker + Docker Compose |
| Monitoring | Prometheus + Grafana |
| CI/CD | GitHub Actions + GitLab CI |
| Schema Validation | Pydantic v2 |
| Export Formats | SARIF v2.1.0, Markdown, JSON |

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/architecture/ARCHITECTURE.md) | System design and component details |
| [Canonical Schema](docs/architecture/CANONICAL_SCHEMA.md) | Finding data model specification |
| [API Reference](docs/setup/API-Documentation.md) | All REST API endpoints |
| [Policy Engine](docs/POLICY_ENGINE.md) | Policy-as-code configuration reference |
| [Competitive Analysis](docs/COMPETITIVE_ANALYSIS.md) | Market positioning and feature comparison |
| [Testing Report](docs/TESTING_REPORT.md) | Deep-code audit and coverage analysis |
| [Cloud Deployment](docs/setup/Cloud-Deployment.md) | AWS / GCP / Azure deployment guide |
| [Token Setup](docs/setup/TOKEN_SETUP.md) | GitHub & GitLab token configuration |
| [Changelog](CHANGELOG.md) | Version history and release notes |
| [Contributing](CONTRIBUTING.md) | Contribution guidelines |
| **Evaluation** | |
| [Evaluation Report](docs/evaluation/EVALUATION.md) | Precision/recall, OWASP coverage, competitive analysis |
| [Per-Tool Evaluation](docs/evaluation/PER_TOOL_EVALUATION.md) | Per-engine accuracy across 4 vulnerable repos |
| [User Study](docs/evaluation/USER_STUDY.md) | A/B comparison: raw tools vs ACR-QA |

---

## 🎓 Academic Context

| | |
|-|-|
| **Student** | Ahmed Mahmoud Abbas |
| **Supervisor** | Dr. Samy AbdelNabi |
| **Institution** | King Salman International University (KSIU) |
| **Timeline** | October 2025 – June 2026 |
| **Status** | Phase 1 ✅ Complete · Phase 2 🔄 In Progress |

### Phase 2 Roadmap (Feb–Jun 2026)

- [x] ~~Quality gates, per-repo config, inline suppression, dedup~~ (v1.0)
- [x] ~~Deep-code audit + 100 tests + bug fixes~~ (v2.6)
- [x] ~~Competitive features: test gap analyzer, OWASP compliance, policy engine, feedback tuner, confidence filtering~~ (v2.7)
- [x] ~~God-mode testing: 474 tests across 14 test suites~~ (v3.0.8 → 526 tests at v3.1.1)
- [x] ~~JavaScript / TypeScript language adapter~~ (v3.0.3) — ESLint, Semgrep JS, npm audit, 56 rule mappings
- [x] ~~Confidence Scoring Engine — 0-100 score per finding, DB-stored, dashboard slider~~ (v3.0.8)
- [x] ~~Go language adapter~~ (v3.2.0) — gosec, staticcheck, Semgrep Go rules
- [ ] User study (8–10 participants)
- [ ] Precision / recall evaluation against ground-truth labels
- [ ] ☁️ Cloud deployment on DigitalOcean ($200 free credit via GitHub Student Pack)
  - Docker Compose on cloud droplet (zero code changes)
  - Nginx reverse proxy + Let's Encrypt SSL
  - Live PR webhook integration (real-time analysis on PR open)
  - Sentry error tracking (free via GitHub Student Pack)
- [ ] Inline PR fix suggestions (requires live deployment)
- [ ] Historical trend comparison (requires accumulated run data)
- [ ] 5-minute demo video

### Phase 3 — Bonus Features ⭐ (Deployment-Enabled Stretch Goals)

> These are **bonus goals** enabled by the cloud deployment. They expand ACR-QA from a graduation project into a production-ready platform.

**Deployment-Enabled (Apr–Jun 2026):**
- [ ] 🔌 GitHub App — one-click install on any repo (no YAML copying)
- [ ] 🌐 Public demo instance — paste a GitHub URL, get instant analysis
- [ ] 📊 Remote user study — participants evaluate via public URL
- [ ] 📈 Historical trend dashboard — 30-day rolling quality metrics in Grafana
- [ ] 🏷️ Code quality badge service — dynamic SVG badges for repo READMEs
- [ ] 💬 Chat notifications — Telegram/Slack alerts on critical findings
- [ ] 🌙 Scheduled nightly scans — cron-triggered full-repo analysis + daily reports

**Post-Graduation Vision:**
- [ ] 🏫 Classroom mode + leaderboard — professor creates class, students ranked by code quality
- [ ] 🧩 VS Code extension — real-time inline warnings as you type

---

## 📄 License

MIT License — see [LICENSE](LICENSE)

---

<div align="center">

Built with ❤️ at King Salman International University · <a href="https://github.com/ahmed-145/acr-qa">⭐ Star this repo</a>

</div>
