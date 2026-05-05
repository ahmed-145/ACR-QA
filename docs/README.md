# ACR-QA Documentation Index

## 📐 Architecture

| Document | Description |
|----------|-------------|
| [C1 Context](architecture/c1-context.md) | System in its environment — users, GitHub, Groq, Prometheus |
| [C2 Containers](architecture/c2-containers.md) | Deployable units — CLI, engine, dashboard, PostgreSQL, Redis |
| [C3 Components](architecture/c3-components.md) | Inside the engine — adapters, normalisers, AI layer, advanced engines |
| [C4 Code](architecture/c4-code.md) | Single finding lifecycle from raw tool output to PostgreSQL |
| [Architecture (detailed)](architecture/ARCHITECTURE.md) | Pipeline stages, component design, database schema, security |
| [Canonical Schema](architecture/CANONICAL_SCHEMA.md) | Universal finding data model with field reference |
| [Internal API](architecture/API.md) | Python class/function API reference for all components |

## 📋 Architecture Decision Records

| ADR | Decision |
|-----|----------|
| [0001 — Context & Goals](adr/0001-context-and-goals.md) | Scope: self-hosted thesis tool, not SaaS |
| [0002 — Multi-Tool Adapter Pattern](adr/0002-multi-tool-adapter-pattern.md) | LanguageAdapter ABC for language support |
| [0003 — RAG over Generic LLM](adr/0003-rag-over-generic-llm.md) | RAG + semantic entropy for hallucination control |
| [0004 — Groq as LLM Provider](adr/0004-groq-as-llm-provider.md) | Free tier, 500+ tok/s, 4-key rotation |
| [0005 — PostgreSQL for Provenance](adr/0005-postgres-for-provenance.md) | ACID, relational audit trail, concurrent CI runners |

## 🔧 Setup & Configuration

| Document | Description |
|----------|-------------|
| [REST API Reference](API_REFERENCE.md) | All 22 HTTP endpoints, CLI reference, JS fetch() integration example [v3.0] |
| [REST API (legacy)](setup/API-Documentation.md) | Original 11 HTTP endpoints reference (v2.7) |
| [Cloud Deployment](setup/Cloud-Deployment.md) | PythonAnywhere, Replit, ngrok deployment guides |
| [Token Setup](setup/TOKEN_SETUP.md) | GitHub, GitLab, and Groq API key configuration |
| [LLM Providers](setup/LLM_PROVIDERS.md) | Groq (default) + AgentRouter integration plan, model comparison, budget planning |
| [Policy Engine](POLICY_ENGINE.md) | `.acrqa.yml` config reference — rules, thresholds, autofix, AI |

## 🧪 Testing & Quality

| Document | Description |
|----------|-------------|
| [Testing & Calibration](TESTING_AND_CALIBRATION.md) | Full test suite breakdown, code audit bugs, mass repo testing across 9 repos, god-mode end-to-end validation (v2.9), all calibration fixes |

## 📊 Evaluation

| Document | Description |
|----------|-------------|
| [Evaluation Report](evaluation/EVALUATION.md) | Precision/recall/F1, confusion matrix, DVPWA ground truth, comparative benchmarks, OWASP coverage, competitive analysis |
| [Per-Tool Evaluation](evaluation/PER_TOOL_EVALUATION.md) | Per-engine accuracy analysis: Bandit, Semgrep, Ruff, Vulture, Radon, jscpd across 4 vulnerable repos |
| [User Study](evaluation/USER_STUDY.md) | A/B comparison materials: raw tool output vs ACR-QA with AI explanations |
| [User Study Protocol](evaluation/USER_STUDY_PROTOCOL.md) | 20-minute structured user study protocol, 3 test scenarios, researcher script, data recording table |
| [User Study Survey](evaluation/USER_STUDY_SURVEY.md) | 15-question participant questionnaire for formal evaluation |

## 🎓 Presentation

| Document | Description |
|----------|-------------|
| [Presentation Script](PRESENTATION_SCRIPT.md) | 7-min presentation script, Q&A cheat sheet, demo commands (all in one) |
| [Demo Video Script](DEMO_VIDEO_SCRIPT.md) | 5-minute structured demo video script with timestamps and voiceover narration |
| [LaTeX Slides](acr_qa_presentation.tex) | Formal presentation slide source |
| [Phase 1 Extras](thesis/Phase1-extras.md) | Additional Phase 1 implementation details |

## 🚨 SRE & Operations

| Document | Description |
|----------|-------------|
| [SLOs](sre/slos.md) | 4 formal SLOs — availability 99.5%, P95 < 500ms, scan completion 99%, AI latency < 5s |
| [Runbook: Groq API Down](sre/runbooks/groq-api-down.md) | Rate limiting, key rotation, graceful degradation |
| [Runbook: High 5xx Rate](sre/runbooks/high-error-rate-5xx.md) | Diagnosis and resolution by root cause |
| [Runbook: DB Connection Pool](sre/runbooks/db-connection-pool-exhausted.md) | Terminate idle connections, max_connections tuning |
| [Runbook: Disk Full (Postgres)](sre/runbooks/disk-full-postgres.md) | VACUUM, data retention, volume monitoring |
| [Runbook: Restore from Backup](sre/runbooks/restore-from-backup.md) | Full restore procedure with estimated recovery times |

## 🚀 Deployment

| Document | Description |
|----------|-------------|
| [Railway Preview Deploys](setup/RAILWAY_DEPLOY.md) | PR preview environments via Railway (GitHub Student Pack) |
| [Cloud Deployment](setup/Cloud-Deployment.md) | PythonAnywhere, Replit, ngrok deployment guides |

## 🗺️ Roadmap

| Document | Description |
|----------|-------------|
| [ROADMAP](ROADMAP.md) | Phase 1 (Python v3.0, complete), Phase 1B (JS adapter), Phase 2 (full TS rewrite — architecture, stack, implementation order) |

## 📁 Project Root Docs

| Document | Description |
|----------|-------------|
| [README](../README.md) | Project overview, features, quick start |
| [CHANGELOG](../CHANGELOG.md) | Version history and release notes |
| [CONTRIBUTING](../CONTRIBUTING.md) | Development setup and contribution guidelines |
| [SECURITY](../SECURITY.md) | Security policy and vulnerability reporting |
| [PERFORMANCE_BASELINE](PERFORMANCE_BASELINE.md) | Pipeline timing benchmarks |

## 📊 Generated Documentation

During analysis runs, ACR-QA generates:
- **Reports:** `DATA/outputs/report_run_*.md`
- **Provenance:** `DATA/outputs/provenance/`
- **SARIF:** `DATA/outputs/*.sarif`
- **Compliance:** Via `scripts/generate_compliance_report.py`

---

**Last Updated:** May 5, 2026
