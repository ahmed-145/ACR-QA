<div align="center">

# 🛡️ ACR-QA
### Automated Code Review & Quality Assurance Platform

*Intelligent, context-aware code analysis with RAG-enhanced AI explanations*

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![CI Tests](https://github.com/ahmed-145/ACR-QA/actions/workflows/tests.yml/badge.svg)](https://github.com/ahmed-145/ACR-QA/actions/workflows/tests.yml)
[![Tests](https://img.shields.io/badge/Tests-97%20passing-22c55e?logo=pytest&logoColor=white)](./TESTS/)
[![Version](https://img.shields.io/badge/Version-2.5.0-blue)](CHANGELOG.md)
[![PostgreSQL 15](https://img.shields.io/badge/PostgreSQL-15+-336791?logo=postgresql&logoColor=white)](https://postgresql.org/)
[![Prometheus](https://img.shields.io/badge/Prometheus-monitored-e6522c?logo=prometheus&logoColor=white)](https://prometheus.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[Quick Start](#-quick-start) · [Architecture](#-architecture) · [Dashboard](#-dashboard) · [Monitoring](#-monitoring) · [GitHub Integration](#-github-pr-integration) · [Docs](#-documentation)

</div>

---

## 🎯 What is ACR-QA?

ACR-QA is a **provenance-first, AI-augmented code review platform**. It runs 6 static analysis tools in parallel, normalises every finding into a canonical schema, and generates evidence-grounded explanations using Retrieval-Augmented Generation (RAG) — all at **zero recurring cost** (free-tier APIs).

Designed as an academic thesis project at KSIU, it covers the full code-review lifecycle: detection → explanation → feedback → CI/CD integration → monitoring.

---

## ✨ Features

### 🔍 Multi-tool Detection
| Tool | What it catches |
|------|----------------|
| **Ruff** | Style, imports, unused code, PEP8 |
| **Semgrep** | Security patterns (OWASP Top 10), custom rules |
| **Bandit** | Python security vulnerabilities |
| **Vulture** | Dead code, unreachable branches |
| **Radon** | Cyclomatic complexity, maintainability index |
| **Secrets Detector** | API keys, passwords, JWTs, tokens |
| **SCA Scanner** | Known-vulnerable dependency versions |

### 🧠 AI Explanations (RAG-Enhanced)
- **Evidence-grounded prompts** — never explains a rule it can't cite
- **Semantic entropy scoring** — runs LLM 3× to measure consistency (hallucination detection)
- **Self-evaluation** — LLM rates its own output on relevance / accuracy / clarity (1–5)
- **Confidence badges** — 🎯 color-coded per finding on the dashboard

### 🔧 Auto-Fix Engine
- Generates before/after code diffs for 8 fixable rule categories
- Per-rule confidence scores (60–95%)
- Fix verification — re-runs Ruff on the patched code to confirm the violation is resolved
- `--auto-fix` CLI flag

### 📊 Dashboard & API
- Real-time severity breakdown (Critical / Warning / Info)
- Full-text search, severity + category filters
- Trend charts (per-run severity over time)
- 💰 **Cost-benefit widget** — analysis cost, hours saved, ROI ratio
- False-positive feedback buttons on every finding
- Prometheus `/metrics` endpoint for external monitoring

### 🔒 Security & Compliance
- OWASP / SANS compliance tagging
- SARIF v2.1.0 export (`scripts/export_sarif.py`) → GitHub Security tab
- Complete provenance tracking (every LLM call stored with prompt + response)

### 🚀 CI/CD
- GitHub Actions workflow (auto-triggers on PR open / sync / comment `acr-qa review`)
- GitLab CI pipeline (`.gitlab-ci.yml`)
- `--diff-only` flag analyzes only changed files
- Posts severity-sorted PR comments automatically

---

## 🚀 Quick Start

### Option A — Docker (Recommended, one command)

```bash
# 1. Clone
git clone https://github.com/ahmed-145/acr-qa.git && cd acr-qa

# 2. Configure
cp .env.example .env          # add your CEREBRAS_API_KEY

# 3. Start everything
make up
```

That's it. `make up` starts:

| Service | URL | Purpose |
|---------|-----|---------|
| 📊 Dashboard | http://localhost:5000 | Flask web UI |
| 📈 Grafana | http://localhost:3000 | Monitoring dashboards (admin/admin) |
| 🔥 Prometheus | http://localhost:9090 | Metrics scraping |
| 🗄️ PostgreSQL | localhost:5433 | Database |
| 🔴 Redis | localhost:6379 | Rate limiting & caching |

### Option B — Local (no Docker)

```bash
# Prerequisites: Python 3.11+, PostgreSQL 15+, Node.js 18+
pip install -r requirements.txt
pip install ruff semgrep vulture radon bandit
npm install -g jscpd

createdb acrqa
psql -d acrqa -f DATABASE/schema.sql

cp .env.example .env   # fill in credentials
source .env
python3 FRONTEND/app.py   # → http://localhost:5000
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        ACR-QA Pipeline                          │
│                                                                  │
│  GitHub PR ──►  Detection Layer  ──►  Normaliser  ──►  Scorer  │
│                 ┌────────────┐       ┌──────────┐    ┌───────┐  │
│                 │ Ruff       │       │ Canonical│    │ HIGH  │  │
│                 │ Semgrep    │──────►│ Schema   │───►│ MED   │  │
│                 │ Bandit     │       │ (Finding)│    │ LOW   │  │
│                 │ Vulture    │       └──────────┘    └───┬───┘  │
│                 │ Radon      │                           │      │
│                 │ Secrets    │                           ▼      │
│                 │ SCA        │              ┌────────────────┐  │
│                 └────────────┘              │  RAG Explainer │  │
│                                            │  rules.yml KB  │  │
│                                            │  Cerebras LLM  │  │
│                                            │  + Entropy     │  │
│                                            │  + Self-eval   │  │
│                                            └───────┬────────┘  │
│                                                    │            │
│                 ┌──────────┐                       ▼            │
│                 │Dashboard │◄────── PostgreSQL ◄───────────────┤
│                 │/metrics  │        (provenance)                │
│                 │PR Comment│──────► GitHub API                  │
│                 └──────────┘                                    │
└─────────────────────────────────────────────────────────────────┘
```

### Component Map

```
acr-qa/
├── CORE/
│   ├── main.py                  # Analysis pipeline (AnalysisPipeline class)
│   ├── engines/
│   │   ├── normalizer.py        # Tool output → canonical schema
│   │   ├── severity_scorer.py   # Intelligent severity assignment
│   │   ├── explainer.py         # RAG + LLM + entropy + self-eval
│   │   ├── autofix.py           # Code fix generation + verification
│   │   ├── secrets_detector.py  # API key / credential detection
│   │   └── sca_scanner.py       # Dependency vulnerability scanning
│   └── utils/
│       ├── code_extractor.py    # Context window extraction
│       └── metrics.py           # Prometheus counters & histograms
├── DATABASE/
│   ├── schema.sql               # Idempotent PostgreSQL schema (IF NOT EXISTS)
│   └── database.py              # DB interface with reconnection logic
├── FRONTEND/
│   ├── app.py                   # Flask dashboard + API endpoints
│   └── templates/index.html     # Modern dark-mode UI
├── TOOLS/
│   ├── run_checks.sh            # Tool runner (parallel execution)
│   └── semgrep/python-rules.yml # Custom Semgrep rules
├── scripts/
│   ├── post_pr_comments.py      # GitHub PR comment poster
│   ├── export_sarif.py          # SARIF v2.1.0 export
│   ├── export_provenance.py     # Full audit trail export
│   ├── generate_report.py       # Markdown report generator
│   └── generate_pr_summary.py   # PR summary generator
├── config/
│   ├── rules.yml                # RAG knowledge base (rule definitions)
│   ├── prometheus.yml           # Prometheus scrape config
│   └── grafana/                 # Grafana auto-provisioning
│       ├── provisioning/        # Datasource + dashboard providers
│       └── dashboards/          # Pre-built dashboard (6 panels)
├── .github/workflows/acr-qa.yml # GitHub Actions CI/CD
├── .gitlab-ci.yml               # GitLab CI pipeline
├── docker-compose.yml           # Full stack (App + DB + Monitoring)
├── Makefile                     # One-command operations
└── TESTS/                       # 77-test pytest suite
```

---

## 📊 Dashboard

Access at **http://localhost:5000**

| Feature | Description |
|---------|-------------|
| Severity counters | Critical / Warning / Info with live counts |
| 💰 Cost-benefit widget | Analysis cost, hours saved, ROI ratio, cost/finding |
| Severity trends chart | Per-run breakdown over last 30 runs |
| Finding cards | Collapsible with AI explanation, code snippet, 🎯 confidence badge |
| False-positive buttons | Mark FP or give helpful/not-helpful feedback |
| Filters | By severity, category, and full-text search |
| Export | SARIF, provenance trace, Markdown reports |

---

## 📈 Monitoring

### Prometheus
ACR-QA exposes a `/metrics` endpoint compatible with Prometheus. When running via Docker, Prometheus auto-scrapes it every 15 seconds.

Available metrics:
```
acrqa_http_requests_total{endpoint, method, status_code}
acrqa_http_request_duration_seconds{endpoint}
```

### Grafana Dashboards
Pre-built dashboard with **6 panels** auto-loads at **http://localhost:3000** (admin/admin):

| Panel | Query |
|-------|-------|
| 🌐 Request Rate | `rate(acrqa_http_requests_total[5m])` |
| ⏱️ Response Time P95/P50 | `histogram_quantile(0.95, ...)` |
| 📊 Total Requests (stat) | `sum(acrqa_http_requests_total)` |
| ✅ HTTP Success Rate | `2xx / total * 100` |
| 🧠 LLM Latency (gauge) | `avg(explain endpoint duration)` |
| 🔴 Error Rate | `rate(5xx responses[1m])` |

---

## 🔗 GitHub PR Integration

### Automatic (on PR open/sync)
The `.github/workflows/acr-qa.yml` workflow fires automatically on every PR. It:
1. Detects changed files (Python / JS / TS / Java)
2. Runs ACR-QA on the diff only (`--diff-only`)
3. Posts severity-sorted comments on the PR

**Required secrets** (set in repo Settings → Secrets):
```
CEREBRAS_API_KEY   # AI explanations
GITHUB_TOKEN       # Automatically provided by Actions
```

### Manual Trigger
Comment on any PR:
```
acr-qa review
```
The bot reacts with 👀 then 🚀 when done.

### GitLab
`.gitlab-ci.yml` provides the same functionality for GitLab repositories. Set `CEREBRAS_API_KEY` and `GITLAB_TOKEN` in CI/CD Variables.

---

## 💻 CLI Reference

```bash
python3 CORE/main.py [options]

Options:
  --target-dir DIR     Directory to analyze (required)
  --repo-name NAME     Repository name for provenance tracking
  --pr-number N        PR number (enables PR comment posting)
  --limit N            Max findings to process (default: 50)
  --diff-only          Analyze changed files only (uses git diff)
  --diff-base BRANCH   Base branch for diff (default: main)
  --auto-fix           Generate auto-fix suggestions for fixable rules
```

```bash
# Examples
python3 CORE/main.py --target-dir ./myproject --limit 100
python3 CORE/main.py --target-dir . --diff-only --diff-base main
python3 CORE/main.py --target-dir . --auto-fix

# Export SARIF for GitHub Security tab
python3 scripts/export_sarif.py --run-id <RUN_ID> --output findings.sarif

# Generate Markdown report
python3 scripts/generate_report.py <RUN_ID>

# View full provenance trace
python3 scripts/export_provenance.py <RUN_ID>
```

---

## 🧪 Testing

```bash
# Full pytest suite (77 tests)
make test-all

# Acceptance tests only
make test

# Run analysis on sample files
make run

# End-to-end with Docker
make test-e2e
```

**Test coverage:** 97 passing, 4 skipped (infrastructure-dependent)

Test files in `TESTS/`:
- `test_acceptance.py` — pipeline acceptance tests
- `test_api.py` — all Flask API endpoints
- `test_explainer.py` — RAG + LLM integration
- `test_normalizer.py` — Ruff / Bandit / Semgrep normalisation
- `test_new_engines.py` — secrets detector, SCA, autofix
- `test_pydantic_validation.py` — schema validation
- `test_rate_limiting.py` — Redis rate limiter
- `test_integration_benchmarks.py` — performance benchmarks

---

## 🔬 Thesis Evaluation

**Research Questions:**

| RQ | Question | Implementation | Metric |
|----|----------|----------------|--------|
| RQ1 | Can RAG reduce LLM hallucination? | rules.yml KB + evidence-grounded prompts + entropy scoring | `consistency_score` field (0–1) |
| RQ2 | How to ensure provenance? | Full PostgreSQL audit trail per LLM call | `llm_explanations` table |
| RQ3 | What confidence scoring works? | Per-finding 0.0–1.0 score based on rule citation + entropy | `confidence_score` + `self_eval_score` |
| RQ4 | Does it match industry tools? | 6-tool pipeline vs CodeRabbit / SonarQube | Feature parity table below |

**Industry Feature Parity:**

| Feature | CodeRabbit | SonarQube | ACR-QA |
|---------|------------|-----------|--------|
| Multi-tool analysis | ✅ | ✅ | ✅ (7 tools) |
| AI explanations | ✅ | ✅ | ✅ RAG + entropy |
| Source citations | ✅ | ✅ | ✅ rule ID links |
| Auto-fix suggestions | ✅ | ✅ | ✅ with verification |
| **Quality Gates** | ✅ | ✅ | ✅ configurable |
| **Inline suppression** | ✅ | ✅ | ✅ `# acr-qa:ignore` |
| **Per-repo config** | ✅ | ✅ | ✅ `.acrqa.yml` |
| **Finding dedup** | ✅ | ✅ | ✅ tool-priority |
| GitHub CI/CD | ✅ | ✅ | ✅ |
| GitLab CI/CD | ✅ | ✅ | ✅ |
| SARIF export | ✅ | ✅ | ✅ v2.1.0 |
| OWASP compliance | ⚠️ | ✅ | ✅ |
| Secrets detection | ✅ | ✅ | ✅ |
| SCA scanning | ✅ | ✅ | ✅ |
| Cost-benefit analysis | ❌ | ❌ | ✅ |
| Hallucination detection | ❌ | ❌ | ✅ entropy |
| Recurring cost | $$$  | $$$  | ✅ $0 |

---

## 🛠️ Technology Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11 |
| Web Framework | Flask 3.x |
| Database | PostgreSQL 15 |
| Cache / Rate Limiting | Redis 7 |
| AI Model | Cerebras Llama 3.1 8B (free tier) |
| Static Analysis | Ruff, Semgrep, Bandit, Vulture, Radon |
| Containerisation | Docker + Docker Compose |
| Monitoring | Prometheus + Grafana |
| CI/CD | GitHub Actions + GitLab CI |
| Export | SARIF v2.1.0, Markdown, JSON |
| Validation | Pydantic v2 |

---

## 🎬 Demo

> 📹 *5-minute demo video — coming soon*

---

## 📚 Documentation

- [Architecture Details](docs/architecture/ARCHITECTURE.md)
- [Canonical Schema](docs/architecture/CANONICAL_SCHEMA.md)
- [API Reference](docs/setup/API-Documentation.md)
- [Cloud Deployment Guide](docs/setup/Cloud-Deployment.md)
- [Token Setup (GitHub / GitLab)](docs/setup/TOKEN_SETUP.md)

---

## 🎓 Academic Context

| | |
|-|-|
| **Student** | Ahmed Mahmoud Abbas — ID: 222101213 |
| **Supervisor** | Dr. Samy AbdelNabi |
| **Institution** | King Salman International University (KSIU) |
| **Timeline** | October 2025 – June 2026 |
| **Status** | Phase 1 ✅ Complete · Phase 2 🔄 In Progress |

### Phase 2 Roadmap (Feb–Jun 2026)
- [ ] JavaScript / TypeScript adapter
- [ ] User study (8–10 participants)
- [ ] Precision / recall evaluation against ground-truth labels
- [ ] Production deployment
- [ ] 5-minute demo video

---

## 📄 License

MIT License — see [LICENSE](LICENSE)

---

<div align="center">
Built with ❤️ at King Salman International University · <a href="https://github.com/ahmed-145/acr-qa">⭐ Star this repo</a>
</div>
