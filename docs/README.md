# ACR-QA Documentation Index

> **As of v5.0.0rc2 (June 2026):** All God-Mode tracks through v11 complete; X1–X6 empirical battery.
> Tests: **3,017** (2,954 Python + 63 TS), **87% CORE coverage**. Migrations: **20**. Endpoints: **52**.
> Ground-truth YAMLs: **23** (CVE recall battery: 20 pre-registered).
> Headline result: **P4 Confirmed Tier — 96.4% conservative precision** (95% CI [90.9%, 100%]),
> 100% CVE recall, F1=98.2%. See [evaluation chapter](EVALUATION_CHAPTER.md) ·
> **[full evaluation index →](evaluation/README.md)**.
> Engines documented under [engines/](engines/).

**Quick nav:** [evaluation/](evaluation/README.md) · [architecture/](architecture/) · [adr/](adr/) ·
[business/](business/) · [legal/](legal/) · [setup/](setup/) · [sre/](sre/) · [engines/](engines/) ·
[archive/](archive/) · Defense: [QA_PREP](QA_PREP.md) + [DEFENSE_QA](DEFENSE_QA.md) ·
Plan: [GOD_MODE_V11](GOD_MODE_V11_PERFECT_TEN_ALL_PERSPECTIVES.md) · [ACTIVE_ROADMAP](ACTIVE_ROADMAP.md)

## 🆕 v5.0.0 Engines + Eval Infrastructure

| Document | Description |
|----------|-------------|
| [God Mode v4 Plan (completed)](archive/GOD_MODE_V4_PLAN.md) | All P1–P4 + X1–X5 tracks complete (2026-05-31). Headline: P4 Confirmed Tier 96.4% / 100%. |
| [IaC Scanner](engines/iac_scanner.md) | 28 canonical rules across Terraform / Kubernetes / Dockerfile · `POST /v1/scans/iac` · A.2 |
| [Time-Travel Analyzer](engines/time_travel.md) | Bounded `git log -L` history for any finding · `GET /v1/findings/{fid}/history` · A.2 |
| [Heuristic Risk Predictor](engines/risk_predictor.md) | 0–100 per-file score from 6 transparent features (NOT ML) · `GET /v1/runs/{rid}/risk-map` · A.3 |
| [Head-to-Head Benchmark (X5)](evaluation/HEAD_TO_HEAD_BENCHMARK.md) | 3-way: ACR-QA vs Bandit vs Semgrep — same corpus, same triage. |
| [Confirmed Tier (P4)](evaluation/CONFIRMED_TIER.md) | 4-criterion stratum: 96.4% conservative / 100% optimistic / F1=98.2%. |
| [Benchmark v5](evaluation/BENCHMARK_v5.md) | Auto-generated: 23 ground-truth YAMLs · 46 expected findings · A.3/A.4 |

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
| [REST API Reference](API_REFERENCE.md) | All 52 FastAPI endpoints under `/v1/`, CLI reference, auth flows |
| [Cloud Deployment](setup/Cloud-Deployment.md) | PythonAnywhere, Replit, ngrok deployment guides |
| [Token Setup](setup/TOKEN_SETUP.md) | GitHub, GitLab, and Groq API key configuration |
| [LLM Providers](setup/LLM_PROVIDERS.md) | Groq (default) + Ollama (offline) + AgentRouter; model comparison, `ACRQA_LLM_PROVIDER` env var |
| [Offline Setup](setup/OFFLINE_SETUP.md) | Air-gapped mode — Ollama + OSV snapshot; `ACRQA_MODE=offline` walkthrough |
| [Privacy](legal/PRIVACY.md) | Per-mode data-flow disclosure: cloud / hybrid / offline egress table |
| [Policy Engine](POLICY_ENGINE.md) | `.acrqa.yml` config reference — rules, thresholds, autofix, AI |
| [Railway Deploy](setup/RAILWAY_DEPLOY.md) | Cloud deploy with PostgreSQL + Redis + Alembic migrations |

## 🧪 Testing & Quality

| Document | Description |
|----------|-------------|
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
| [Defense Q&A](DEFENSE_QA.md) | Full defense-day Q&A — precision tables, Confirmed Tier, head-to-head numbers, anti-tautology defense |
| [Defense Deck](DEFENSE_DECK.tex) | 25-slide Beamer metropolis defense slide deck |
| [Demo Video Script](business/DEMO_VIDEO_SCRIPT.md) | 5-minute structured demo video script with timestamps and voiceover narration |
| [LaTeX Slides (legacy)](acr_qa_presentation.tex) | Earlier presentation source |

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
| [God Mode v11 Plan (active)](GOD_MODE_V11_PERFECT_TEN_ALL_PERSPECTIVES.md) | Dual-scoreboard (thesis + startup) plan. Earlier v4–v10 plans archived under [archive/](archive/). |
| [Active Roadmap](ACTIVE_ROADMAP.md) | Current execution log. |
| [Evaluation Integrity Charter](evaluation/INTEGRITY.md) | Pre-registration commitment, scoring rules, skipped-CVE log, adversarial review checklist. |

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
| `CLAUDE.md` (repo root) | **Read first.** Commands, architecture, change protocol, critical rules, repo layout, environment. |
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

**Last Updated:** June 10, 2026
