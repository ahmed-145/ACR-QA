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
| [REST API Reference](API_REFERENCE.md) | All 36 FastAPI endpoints under `/v1/`, CLI reference, auth flows [v4.5.0] |
| [Cloud Deployment](setup/Cloud-Deployment.md) | PythonAnywhere, Replit, ngrok deployment guides |
| [Token Setup](setup/TOKEN_SETUP.md) | GitHub, GitLab, and Groq API key configuration |
| [LLM Providers](setup/LLM_PROVIDERS.md) | Groq (default) + Ollama (offline) + AgentRouter; model comparison, `ACRQA_LLM_PROVIDER` env var |
| [Offline Setup](setup/OFFLINE_SETUP.md) | Air-gapped mode — Ollama + OSV snapshot; `ACRQA_MODE=offline` walkthrough |
| [Privacy](PRIVACY.md) | Per-mode data-flow disclosure: cloud / hybrid / offline egress table |
| [Policy Engine](POLICY_ENGINE.md) | `.acrqa.yml` config reference — rules, thresholds, autofix, AI |
| [Railway Deploy](setup/RAILWAY_DEPLOY.md) | Cloud deploy with PostgreSQL + Redis + Alembic migrations |

## 🧪 Testing & Quality

| Document | Description |
|----------|-------------|
| [**God Mode Plan v2 — §9 Testing Strategy**](GOD_MODE_PLAN.md#9-testing-strategy--read-this-before-writing-any-code) | **6-layer testing pyramid for a security tool. Why coverage % is a tripwire, not a target. The plan to move thesis claims from hand-typed to test-generated.** |
| [Phase 0 Baseline — Reality Check](evaluation/PHASE_0_BASELINE.md) | **May 6, 2026.** Real numbers from running ACR-QA on DVPWA, Pygoat, VulPy, DSVW, Flask, httpx. DVPWA "50% recall" is a tooling limit not a bug; 35 CUSTOM-* rules leaking; parallel-scan DB collision bug. |
| **`TESTS/evaluation/ground_truth/*.yml`** | Ground truth lives in YAML — auditable. Each entry declares `expected_findings`, `out_of_scope` reasons, `recall_target`. Runs nightly via `pytest -m slow`. |
| [Testing & Calibration](TESTING_AND_CALIBRATION.md) | Full test suite breakdown, code audit bugs, mass repo testing across 9 repos, god-mode end-to-end validation (v2.9), all calibration fixes |

## 📊 Evaluation

| Document | Description |
|----------|-------------|
| [Evaluation Report](evaluation/EVALUATION.md) | Precision/recall/F1, confusion matrix, DVPWA ground truth, comparative benchmarks, OWASP coverage, competitive analysis |
| [Per-Tool Evaluation](evaluation/PER_TOOL_EVALUATION.md) | Per-engine accuracy analysis: Bandit, Semgrep, Ruff, Vulture, Radon, jscpd across 4 vulnerable repos |
| [User Study](evaluation/USER_STUDY.md) | A/B comparison materials: raw tool output vs ACR-QA with AI explanations |
| [User Study Protocol](evaluation/USER_STUDY_PROTOCOL.md) | 20-minute structured user study protocol, 3 test scenarios, researcher script, data recording table |
| [User Study Survey](evaluation/USER_STUDY_SURVEY.md) | 15-question participant questionnaire for formal evaluation |
| [User Study Results](evaluation/USER_STUDY_RESULTS.md) | Participant responses tracker — ≥10 participants, A/B fix time + confidence scores |

## 🎓 Presentation

| Document | Description |
|----------|-------------|
| [Presentation Script](PRESENTATION_SCRIPT.md) | 7-min presentation script, Q&A cheat sheet, demo commands (all in one) |
| [Demo Video Script](DEMO_VIDEO_SCRIPT.md) | 5-minute structured demo video script with timestamps and voiceover narration |
| [LaTeX Slides](acr_qa_presentation.tex) | Formal presentation slide source |
| [Blog Post Draft](BLOG_POST_DRAFT.md) | 1500-word technical post — taint+autofix combo, competitive moats, engineering discipline |
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

## 🗺️ Strategy & Roadmap

| Document | Description |
|----------|-------------|
| [**UI Phase 3 Plan**](UI_PHASE_3_PLAN.md) | **Live next step (May 16 2026).** "One killer flow, zero fluff" — marketing landing + killer finding-detail page + public demo mode + smart polish. Target: v4.6.0. |
| [Phase 12 Plan (archived)](archive/PHASE_12_PLAN.md) | Closed May 15 2026 — 37/39 done; only human tasks (demo video + YouTube) remain. |
| [**God Mode Plan v2**](GOD_MODE_PLAN.md) | **v4.0.0 plan (May 5 2026 → May 15 2026).** Three competitive moats + blue-ocean wedge. Completed: 120/128 tasks. Superseded by Phase 12 Plan for next push. |
| [Phase 0 Baseline](evaluation/PHASE_0_BASELINE.md) | Reality check on 6 real repos (May 6 2026); honest current numbers + bugs surfaced + Phase 1 fix log. |
| [ROADMAP (archived)](archive/ROADMAP.md) | Pre-v2 plan. Phase 2 TS rewrite section is explicitly killed by the v2 plan; kept for historical context. |
| [God Mode Plan v1 (archived)](archive/GOD_MODE_PLAN_V1.md) | Original plan — pre-FastAPI/Celery/Auth. Superseded by v2. |

## 🖥 Static UI Dashboard (v4.5.0)

9-page HTML dashboard served at `/ui/` by FastAPI StaticFiles. All pages share dark/light theme,
⌘K command palette, toast notifications, and JWT auth.

| Page | File | Key Feature |
|------|------|-------------|
| Login | `login.html` | JWT login |
| Overview | `index.html` | Gate, stats, quick-action cards |
| Findings | `finding.html` | Detail panel; auto-fix patch; attestation |
| Runs | `runs.html` | Run history; compare + supply-chain deep-links |
| Trends | `trends.html` | SVG trend charts |
| New Scan | `scan.html` | Form + live progress log |
| Compare | `compare.html` | Run-vs-run diff; added/fixed/persisting |
| Supply Chain | `supply-chain.html` | OSV CVEs, dep risk, SBOM export |
| Settings | `settings.html` | Profile, API keys, policy viewer |

## 🤖 AI Agent Onboarding

| Document | Description |
|----------|-------------|
| [AGENTS.md](AGENTS.md) | **Read first.** Universal AI agent instructions: pre-commit checklist, code standards, critical rules, repo layout, environment. |
| [CODEBASE_INDEX.md](CODEBASE_INDEX.md) | Auto-generated AST map of public functions/classes. May be stale — regenerate if needed. |

## 📁 Project Root Docs

| Document | Description |
|----------|-------------|
| [README](../README.md) | Project overview, features, quick start |
| [CHANGELOG](CHANGELOG.md) | Version history and release notes |
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

**Last Updated:** May 16, 2026
