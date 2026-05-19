# ACR-QA Documentation Index

> **As of v5.0.0-beta (May 19, 2026):** Phase A Weeks 1 + 2 of the [God Mode v3 Plan](GOD_MODE_V3_PLAN.md)
> are shipped on `main`. Tests: **2,510** (2,406 Python + 104 TS). Migrations: **14**. Endpoints: **46**.
> Engines documented under [engines/](engines/).

## 🆕 v5.0.0 Engines (in progress)

| Document | Description |
|----------|-------------|
| [Active Plan — God Mode v3](GOD_MODE_V3_PLAN.md) | **Active plan.** 3 phases · 6 calendar weeks Phase A + 12 wk B + 24 wk C. Supersedes v2. |
| [IaC Scanner](engines/iac_scanner.md) | 28 canonical rules across Terraform / Kubernetes / Dockerfile · `POST /v1/scans/iac` · Phase A.2 |
| [Time-Travel Analyzer](engines/time_travel.md) | Bounded `git log -L` history for any finding · `GET /v1/findings/{fid}/history` · Phase A.2 |

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
| [REST API Reference](API_REFERENCE.md) | All 46 FastAPI endpoints under `/v1/`, CLI reference, auth flows [v5.0.0-beta — adds 9 routes: chat, call-graph, history, heatmap, timeline, iac scan] |
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
| [**Master Schedule**](MASTER_SCHEDULE.md) | **⭐ The contract.** 5-week schedule across all plans (W1: risk-first eval → W5: distribution + demo video). Defense runway: 4+ weeks. Single source of truth for sequencing. ~55h total. |
| [UI Phase 3 Plan](UI_PHASE_3_PLAN.md) | W3–W4 of master schedule. "One killer flow, zero fluff" — marketing landing + auth UX + killer finding-detail page + public demo mode + smart polish. Target: v4.6.0. |
| [UI Testing Plan](UI_TESTING_PLAN.md) | W4. 5 unit + 5 E2E + 5 a11y tests + 20-item manual smoke checklist. ~3h. |
| [Eval Bulletproofing Plan](EVAL_EXPANSION_PLAN.md) | W1–W4. Closes the "toy benchmarks" defense critique. **4 tiers:** Tier 0 — Integrity infrastructure (3h, audit script + reproduce target + charter); Tier 1 — CVE Recall Test (15h, 15–20 disclosed Python CVEs as external ground truth); Tier 2 — Peer Validation (3h, inter-rater κ on 20-finding Flask sample); Tier 3 — Corpus Expansion (8h, 4 repos: **govwa Go + Django + TS app + FastAPI**). ~29h total. |
| [Evaluation Integrity Charter](evaluation/INTEGRITY.md) | Tier 0 deliverable. Pre-registration commitment, scoring rules, skipped-CVE log, adversarial review checklist. |
| [Distribution Plan](DISTRIBUTION_PLAN.md) | W5. PyPI release (`pip install acrqa`, 4h) + GitHub Actions Marketplace listing (3h). Converts thesis project into shipped open-source tool. |
| [Phase 12 Plan (archived)](archive/PHASE_12_PLAN.md) | Closed May 15 2026 — 37/39 done; only human tasks (demo video + YouTube) remain. |
| [**God Mode Plan v2**](GOD_MODE_PLAN.md) | **v4.0.0 plan (May 5 2026 → May 15 2026).** Three competitive moats + blue-ocean wedge. Completed: 120/128 tasks. Superseded by Phase 12 Plan for next push. |
| [Phase 0 Baseline](evaluation/PHASE_0_BASELINE.md) | Reality check on 6 real repos (May 6 2026); honest current numbers + bugs surfaced + Phase 1 fix log. |
| [ROADMAP (archived)](archive/ROADMAP.md) | Pre-v2 plan. Phase 2 TS rewrite section is explicitly killed by the v2 plan; kept for historical context. |
| [God Mode Plan v1 (archived)](archive/GOD_MODE_PLAN_V1.md) | Original plan — pre-FastAPI/Celery/Auth. Superseded by v2. |

## Static UI Dashboard (v5.0.0-beta)

13-page HTML dashboard served at `/ui/` by FastAPI StaticFiles. All pages share dark/light theme,
⌘K command palette, toast notifications, JWT auth, and demo mode (`?demo=1`).

| Page | File | Key Feature |
|------|------|-------------|
| Landing | `landing.html` | Hero, proof strip, Live Demo CTA |
| Login | `login.html` | JWT login; gradient CTA; forgot-pw link |
| Sign Up | `signup.html` | Registration + password strength meter |
| Verify | `verify.html` | 6-digit OTP; inline demo code display |
| Forgot PW | `forgot.html` | 3-step reset; simulated email code |
| Overview | `index.html` | Gate, stats, quick-action cards |
| Findings | `finding.html` | Confidence gauge; verdict chips; taint flow; 4 panels |
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
