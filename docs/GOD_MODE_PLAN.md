# ACR-QA God Mode Plan

**Author:** Strategic plan written for Ahmed Mahmoud Abbas — KSIU graduation thesis + career launchpad
**Target career:** Backend Engineering / DevOps / SRE
**Project state at plan start:** v3.2.4 — Python MVP feature-complete, 1690 tests, 86% coverage, 4 Python eval repos at 97.1% precision, Flask dashboard, PostgreSQL + Redis, GitHub Actions CI

---

## 0. The Honest Read

You already have a **thesis-passing project**. What you're about to do is different: you're going to turn this into a **career artifact** — the thing you put at the top of your resume, the thing you talk about in every interview for the next 3 years.

For backend/DevOps roles, recruiters and hiring managers look for **5 signals**:

1. **You can ship production-grade services** (not just scripts that work on your laptop)
2. **You understand systems under load** (caching, queues, async, scaling)
3. **You can operate what you built** (observability, alerting, incident response)
4. **You make explicit architectural decisions** (and document them)
5. **You write code others can read, review, and extend**

The gap between "thesis demo" and "career artifact" is exactly those 5 signals. This plan closes that gap.

---

## 1. North Star — What This Becomes

By the end of god mode, ACR-QA is:

- **A live, deployed SaaS-style service** at `acrqa.fly.dev` (or Railway) anyone can hit
- **Async, scalable, observable** — FastAPI + Celery + Prometheus + OpenTelemetry
- **Multi-tenant ready** — workspaces, API keys, per-user quotas
- **CI/CD that deploys to prod automatically** on green merges to main
- **Documented like a real product** — C4 diagrams, ADRs, runbooks, SLOs
- **Demonstrably under load** — load tests, perf budgets, chaos tests
- **Open-sourced with a real contribution flow** — issues, milestones, releases

You don't need every bullet. You need *enough* that the story holds up in an interview.

---

## 2. The Career Skill ↔ Feature Map

For every feature you build, know which skill it signals. Don't build features for their own sake — build them because they map to a thing you'll be asked about.

| Skill (interview keyword) | Feature you build to signal it | File(s) it touches |
|---|---|---|
| **Async Python / I/O concurrency** | Migrate Flask → FastAPI, async DB | `FRONTEND/app.py` → `FRONTEND/api/`, all endpoints |
| **Message queues / background jobs** | Move analysis to Celery + Redis broker | `CORE/main.py`, new `CORE/tasks.py` |
| **Database migrations** | Alembic for all schema changes | new `alembic/` dir |
| **12-factor / config management** | pydantic-settings, all env-driven | new `CORE/settings.py` |
| **AuthN/AuthZ** | JWT auth + API keys + RBAC roles | new `FRONTEND/auth/` |
| **Caching strategy** | Redis for explanations, fingerprint cache, response cache with stale-while-revalidate | extend existing |
| **Rate limiting / abuse prevention** | Per-tenant token bucket, per-IP fallback | `CORE/utils/rate_limiter.py` |
| **Containers** | Multi-stage Dockerfile, distroless final image, image scan | `Dockerfile` |
| **Kubernetes** | Helm chart with values.yaml, HPA, PDB, NetworkPolicy | new `deploy/helm/` |
| **Infrastructure-as-Code** | Terraform module for Fly.io/Railway/Postgres | new `deploy/terraform/` |
| **Observability — metrics** | Prometheus exporter, Grafana dashboard JSON | extend `CORE/utils/metrics.py` |
| **Observability — logs** | Structured JSON logs, log levels, correlation IDs | `CORE/main.py` setup_logging |
| **Observability — traces** | OpenTelemetry SDK, span around each pipeline stage | new `CORE/observability/tracing.py` |
| **SRE practices** | SLOs, error budget doc, runbook per alert | new `docs/sre/` |
| **Load testing** | Locust scenarios, baseline + regression | new `loadtest/` |
| **API design** | OpenAPI 3.1 spec auto-generated, versioned `/v1/`, webhook system | FastAPI gives this for free |
| **Event-driven architecture** | Outbox pattern → webhook delivery on `analysis.completed` | new `CORE/events/` |
| **CI/CD depth** | Multi-stage pipeline: lint → test → build → deploy preview → deploy prod | `.github/workflows/` |
| **Security mindset** | Auth on dashboard, secrets via Vault/Doppler, dep scanning, SAST in CI, SBOM | various |
| **Operational hygiene** | Backup script, restore drill, migration rollback runbook | `docs/sre/runbooks/` |

If you ship 60% of this list, you can interview at any backend/DevOps shop with confidence. If you ship 100%, you can apply to senior-leaning roles fresh out of school.

---

## 3. Cleanup First — Things to REMOVE

Don't add to a messy codebase. Do this **week 1**, before anything else.

| Remove / Delete | Why |
|---|---|
| `scratch/` directory (extract_highs.py, manual_verify.py, manual_verify_batch.py, verify_all.py) | One-off debugging scripts. Move anything still useful to `scripts/` with proper docstring; delete the rest. |
| Old presentation MDs that target past dates (e.g. `PRESENTATION_SCRIPT.md` for March 11) | Already-shipped milestones. Archive in `docs/archive/` or delete. |
| Duplicate Bandit/Semgrep severity overrides | The duplicate-key purge already started in `severity_scorer.py`. Audit `RULE_MAPPING` in `normalizer.py` for the same pattern. |
| `test_targets/` (if committed by accident) | Eval repos should be downloaded by `scripts/run_evaluation.py`, not committed. Add to `.gitignore`. |
| Flask dashboard `templates/*.html` if you're rewriting frontend | When you split frontend (see §6.4), delete the Jinja templates and serve a real SPA. |
| Any code paths that exist only because Phase 2 (TS rewrite) might happen | Roadmap mentions Phase 2 a lot. Remove any preemptive abstractions added "just in case" — they're noise until you actually start the rewrite. |
| Old "Round 1-5 testing" notes in TESTING_AND_CALIBRATION.md | Compress to a 1-paragraph summary; the round-by-round narrative is thesis-defense ammo, not engineering doc. |

**Concrete action:** open a PR titled `chore: cleanup pre-godmode` that does only deletions and `.gitignore` updates. No new code. This makes the diff for everything that follows much easier to review.

---

## 4. Things to MERGE / CONSOLIDATE

| Merge | Into | Why |
|---|---|---|
| `CORE/engines/secrets_detector.py` + Bandit B105/B106/B107 + Semgrep hardcoded-password rules | A single `SecretsEngine` with a unified `RULE_MAPPING` | Today these three independent paths produce overlapping findings that the deduper has to clean up. One pipeline = less duplication, easier to extend. |
| `CORE/engines/sca_scanner.py` + npm audit (in `js_adapter`) + `pip-audit` (if added) | A single `DependencyEngine` with per-language plugins | Same pattern as above — SCA is one concept; tool fragmentation is an implementation detail. |
| 22 REST endpoints in `FRONTEND/app.py` | Routers split by domain: `runs`, `findings`, `scan`, `quality`, `admin` | One 1500-line `app.py` is a smell. FastAPI's `APIRouter` makes this trivial. |
| `CORE/main.py` (1167 lines) | A `CORE/cli/` package + `CORE/pipeline.py` for orchestration | The CLI args, output formatting, JSON dumping, Rich rendering, and pipeline orchestration are all tangled. Split. |
| Per-language `*_RULE_MAPPING` dicts spread across adapters | A single YAML knowledge base (`config/rules.yml` already exists — extend it) | Today rules live in code (Python dicts). Move them to data; load at startup. Lets you swap rule packs per tenant later. |
| `TESTS/test_god_mode.py` + `test_deep_coverage.py` + `test_integration.py` | Reorganized by feature, not by "vibes" | These names made sense at the time; they don't help a new contributor find tests. Reorganize as `tests/unit/`, `tests/integration/`, `tests/e2e/`. |

---

## 5. Things to CHANGE — The Backend Hardening

This is the meat. Do these in order.

### 5.1 Flask → FastAPI (Week 2-3)

**Why it matters for career:** Every backend job ad in 2026 lists FastAPI or async Python. Flask is fine, but async Flask is awkward; FastAPI gives you async, OpenAPI auto-generation, type-safe request/response models, and dependency injection — all signals that you understand modern Python service design.

**Changes:**
- New entrypoint: `FRONTEND/api/main.py` exposing FastAPI `app`
- All endpoints become `async def`, take Pydantic request models, return Pydantic response models
- Move from `psycopg2` (sync) to `asyncpg` or SQLAlchemy 2.0 async
- Auto-generate OpenAPI spec at `/openapi.json`, Swagger UI at `/docs`
- Keep Flask running in parallel for one release; switch dashboard to call new `/v1/` endpoints

**Resume bullet you earn:** *"Migrated REST API from Flask to async FastAPI, reducing P95 latency on `/api/runs/{id}/findings` from 380ms to 90ms under 50 RPS load."*

### 5.2 Synchronous pipeline → Celery + Redis broker (Week 3)

**Why it matters:** Real services don't block the request thread for 30+ seconds while running 7 analysis tools. They queue the work and return a job ID.

**Changes:**
- New `CORE/tasks.py` with `@celery_app.task` for `run_analysis(target_dir, run_id)`
- `POST /api/v1/scans` returns `202 Accepted` with `{"job_id": "..."}` immediately
- New `GET /api/v1/scans/{job_id}` returns status: `queued | running | completed | failed`
- Worker process: `celery -A CORE.tasks worker --loglevel=info --concurrency=4`
- Add to `docker-compose.yml`: a `worker` service that runs the Celery worker
- Wire up Redis as both broker and result backend (already deployed)

**Resume bullet:** *"Decoupled long-running scans from request path using Celery; sustained 200 concurrent scans on a single worker pod with sub-second API response time."*

### 5.3 Alembic migrations (Week 2)

**Why it matters:** "We use Django migrations" / "We use Alembic" is the first question on a back-end interview about databases. You want a real, multi-revision migration history.

**Changes:**
- `pip install alembic` → `alembic init alembic`
- Generate baseline migration matching current schema: `alembic revision --autogenerate -m "baseline"`
- Every schema change from here goes through `alembic revision`
- CI step: `alembic upgrade head` before tests run
- Add `make db-migrate`, `make db-rollback` targets

**Resume bullet:** *"Implemented zero-downtime schema migrations with Alembic; all schema changes are reviewable diffs and reversible in production."*

### 5.4 Auth — JWT + API keys + RBAC (Week 4)

**Why it matters:** Your `ROADMAP.md` already lists "Flask dashboard has no auth" as a known gap. Closing it is a one-week project that pays for itself in interviews forever.

**Changes:**
- `users` table: id, email, password_hash (bcrypt), role (admin / member / viewer), created_at
- `api_keys` table: id, user_id, key_hash, name, last_used_at, scopes (jsonb)
- `POST /v1/auth/login` → JWT (15min access, 7d refresh)
- `POST /v1/auth/refresh` → rotate refresh token
- All `/v1/*` routes require `Authorization: Bearer <jwt>` OR `X-API-Key: <key>`
- Decorator/dependency `require_role("admin")` for admin routes
- Add `seed_admin.py` script for first-user bootstrap

**Resume bullet:** *"Designed multi-mode auth (JWT for browser, API keys for CI integrations) with bcrypt password hashing and per-key scope enforcement."*

### 5.5 Webhook delivery system + outbox pattern (Week 5)

**Why it matters:** Event-driven architecture is the most undertaught topic in CS programs and the most asked-about in mid-level interviews. Building a real webhook system teaches you idempotency, retries, dead-letter queues, and signing.

**Changes:**
- `events` outbox table: id, event_type, payload (jsonb), created_at, delivered_at, attempts
- After analysis completes: insert row into `events` with `analysis.completed` payload
- Background task: poll outbox, deliver to subscribed webhook URLs, sign with HMAC-SHA256, exponential backoff, dead-letter after 5 attempts
- `webhooks` table: id, user_id, url, secret, event_types (jsonb), is_active
- API: `POST /v1/webhooks`, `DELETE /v1/webhooks/{id}`, `POST /v1/webhooks/{id}/test`

**Resume bullet:** *"Built event-driven webhook delivery with outbox pattern, HMAC request signing, and exponential-backoff retry — guarantees at-least-once delivery."*

### 5.6 Multi-tenancy / workspaces (Week 6, optional but high-impact)

**Why it matters:** SaaS skills. Even if you never build a real SaaS, knowing how to scope data by tenant in queries is a senior-leaning skill.

**Changes:**
- `workspaces` table; every existing data table gets a `workspace_id` FK
- Row-level security: every query filters by `workspace_id` (use SQLAlchemy event listener or middleware)
- Per-workspace quotas: max scans/day, max findings retained
- Per-workspace API keys

---

## 6. Things to ADD — The DevOps Layer

### 6.1 Real Dockerfile (Week 4)

Today's Dockerfile is probably a single-stage `FROM python:3.11`. That's fine for dev, embarrassing for prod.

**New `Dockerfile`:**
- Stage 1: `python:3.11-slim` — install build deps, `pip install --target=/deps`
- Stage 2: `gcr.io/distroless/python3-debian12` — copy `/deps`, copy app code, run as non-root
- Final image < 150MB
- `HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1`
- Multi-arch build (amd64 + arm64) via buildx

### 6.2 Kubernetes (Week 5-6)

You don't need a real K8s cluster. You need a Helm chart that **demonstrates** you understand K8s.

**New `deploy/helm/acrqa/`:**
- `Chart.yaml`, `values.yaml`, `templates/`
- `Deployment` for API (3 replicas), `Deployment` for worker (2 replicas)
- `Service` (ClusterIP) + `Ingress` with TLS via cert-manager annotation
- `HorizontalPodAutoscaler` based on CPU and queue depth (custom metric)
- `PodDisruptionBudget` (min 2 available)
- `NetworkPolicy` (only ingress from ingress-controller, only egress to Postgres+Redis)
- `ConfigMap` for non-secret config, `Secret` for DB password
- `CronJob` for nightly DB backup
- README explaining how to install with `helm install acrqa ./deploy/helm/acrqa`

**Validate it works** with `kind` or `k3d` locally — don't ship untested manifests.

### 6.3 Terraform for cloud deploy (Week 6)

**New `deploy/terraform/`:**
- Module for Fly.io app (or Railway, or DigitalOcean App Platform — pick one free tier)
- Module for managed Postgres (Neon, Supabase, or Fly Postgres)
- Module for managed Redis (Upstash free tier)
- `terraform apply` brings up the entire stack from zero
- Bonus: GitHub Actions step that runs `terraform plan` on every PR, comments the diff

### 6.4 Frontend rewrite — actual SPA (Week 7-8, optional)

The Flask + Jinja dashboard is the weakest part of the project today. A modern frontend earns frontend-adjacent points and de-risks the whole demo.

**New `frontend/`:**
- Vite + React + TypeScript + Tailwind
- Calls `/v1/*` endpoints
- Pages: login, runs list, run detail, finding detail, settings
- Build artifact served by Nginx in production (separate container) or by FastAPI's `StaticFiles` mount in dev
- Lighthouse score > 90

This is the most time-expensive item in this plan. Do it last; skip if running short.

---

## 7. Things to ADD — The SRE / Observability Layer

This is where you go from "I can build" to "I can operate." It's the most career-impactful section.

### 7.1 Prometheus + Grafana (Week 6)

**Changes:**
- Add `prometheus_client` Python lib
- Expose `/metrics` endpoint on API with: request count, latency histogram, error rate, queue depth, scan duration
- Add `prometheus.yml` and `grafana/dashboards/acrqa.json` to repo
- Docker-compose service for both
- Screenshot the dashboard, put in README

**Resume bullet:** *"Instrumented service with Prometheus metrics (RED method); built Grafana dashboard tracking request rate, error rate, and P95 latency per endpoint."*

### 7.2 OpenTelemetry distributed tracing (Week 7)

**Changes:**
- `pip install opentelemetry-distro opentelemetry-instrumentation-fastapi opentelemetry-instrumentation-celery opentelemetry-instrumentation-asyncpg`
- One-line auto-instrumentation
- Manual spans around each pipeline stage (Ruff, Bandit, Semgrep, normalize, score, AI explain)
- Export to Jaeger or Tempo (free tier on Grafana Cloud)
- Each scan produces a trace you can click through to see where time was spent

**Resume bullet:** *"End-to-end distributed tracing across HTTP → Celery → Postgres using OpenTelemetry; debugged a 12-second P99 outlier in 5 minutes by reading traces."*

### 7.3 Structured logging with correlation IDs (Week 6)

You already have `setup_logging(json_output=False)` in `CORE/main.py`. Take it further.

**Changes:**
- Always emit JSON in production (`LOG_FORMAT=json` env var)
- Every log line includes: `timestamp`, `level`, `service`, `trace_id`, `span_id`, `request_id`, `user_id` (if authenticated), `workspace_id`
- Middleware injects request_id from `X-Request-ID` header (or generates one)
- All logs from a single request are joinable by `request_id` in your log aggregator

### 7.4 SLOs + error budgets (Week 7)

Write `docs/sre/slos.md`:

| SLO | Target | Window | Error budget |
|---|---|---|---|
| API availability | 99.5% | 30 days | 3.6 hours/month |
| Scan success rate | 99% | 7 days | 100 failed/10k |
| P95 API latency | < 500ms | 7 days | — |
| Scan completion P95 | < 60s for repos < 10k LOC | 7 days | — |

For each SLO: what we measure, how we alert, what we do when budget is burned.

### 7.5 Runbooks (Week 7-8)

`docs/sre/runbooks/` — one MD per alert/scenario:

- `db-connection-pool-exhausted.md`
- `worker-queue-backed-up.md`
- `high-error-rate-5xx.md`
- `disk-full-postgres.md`
- `groq-api-down.md` (graceful degradation: skip explanations, return cached, return raw findings)
- `restore-from-backup.md`

Each runbook: symptoms, dashboards to check, queries to run, mitigation steps, escalation. **Test at least one with chaos engineering** (e.g. kill the DB during a scan, follow your own runbook).

**Resume bullet:** *"Wrote and validated runbooks for top 6 incident scenarios; demonstrated DB recovery in 4 minutes during chaos drill."*

### 7.6 Load tests (Week 7)

`loadtest/` with Locust scenarios:
- `01_basic_browse.py` — list runs, view findings
- `02_scan_burst.py` — 100 concurrent scan submissions
- `03_realistic_mix.py` — 80% reads / 20% scan submissions / occasional admin

Run on every PR via GitHub Actions, fail the build if P95 regresses by > 20%.

**Resume bullet:** *"Established performance baseline with Locust load tests; CI fails any PR that regresses P95 latency by more than 20%."*

### 7.7 Chaos engineering (Week 8, stretch)

Use `pumba` or `toxiproxy` to inject failures during integration tests:
- Drop 30% of Redis connections — does the API still serve cached responses?
- Add 500ms latency to Postgres — does the worker still finish before timeout?
- Kill Groq API — do scans complete with raw findings?

Document each scenario, the failure mode you found, and the fix.

---

## 8. Things to ADD — Documentation as a Career Asset

The single highest-leverage thing on this list. Documentation is the artifact recruiters can read in 5 minutes.

### 8.1 Architecture diagrams — C4 model (Week 1, do early!)

`docs/architecture/`:
- `c1-context.md` — system in its environment (users, GitHub, AI providers, DB, Redis)
- `c2-containers.md` — API, worker, DB, cache, frontend
- `c3-components.md` — inside the API: routers, services, repositories, adapters
- `c4-code.md` — one example deep-dive (e.g., how a single scan flows through the system)

Use Mermaid (already used in `ROADMAP.md`) or excalidraw. Embed in README.

### 8.2 ADRs — Architecture Decision Records (ongoing)

`docs/adr/` — one MD per significant decision, numbered:
- `0001-flask-to-fastapi.md`
- `0002-celery-vs-rq.md`
- `0003-postgres-vs-sqlite-for-tenants.md`
- `0004-jwt-auth-design.md`
- `0005-multi-language-adapter-pattern.md`

Format: Context → Decision → Consequences → Alternatives considered. **This is the document recruiters love most** — it shows you can think, not just code.

### 8.3 README rewrite

The README is your storefront. Make it sing:
- Animated GIF of the dashboard at the top (use `vhs` or `asciinema`)
- 30-second pitch: what is it, who is it for, why does it exist
- Architecture diagram (C2 from §8.1)
- Quickstart: `docker compose up` → live dashboard at localhost:5000
- Live demo link: `https://acrqa.fly.dev`
- Badges: CI, coverage, license, version, Docker pulls
- "Built with" section listing every major dep — recruiters scan this

### 8.4 CONTRIBUTING + CODE_OF_CONDUCT + SECURITY.md

You already have CONTRIBUTING. Add:
- `SECURITY.md` — how to report vulnerabilities (you're a security tool — this is meta-credibility)
- `CODE_OF_CONDUCT.md` — Contributor Covenant boilerplate
- Issue templates (`.github/ISSUE_TEMPLATE/`)
- PR template (`.github/PULL_REQUEST_TEMPLATE.md`)

### 8.5 Public roadmap + changelog discipline

- Convert `ROADMAP.md` to GitHub Projects board with public visibility
- Every release has a `CHANGELOG.md` entry following Keep a Changelog format
- Tag releases with semver (v3.3.0, v4.0.0, etc.) and write release notes

---

## 9. CI/CD — Make It Production-Grade

`.github/workflows/`:

### 9.1 `ci.yml` (improve existing)

Stages, in this order, fail-fast:
1. **Lint** — ruff + mypy + actionlint + hadolint (Dockerfile lint)
2. **Unit tests** — pytest with coverage; fail if < 85%
3. **Integration tests** — spin up Postgres+Redis via service containers, run integration suite
4. **E2E tests** — playwright against dashboard
5. **Security scan** — Trivy on built image, Bandit on source, Semgrep on source, pip-audit on deps
6. **SBOM generation** — `syft packages dir:. -o spdx-json > sbom.json`, upload as artifact
7. **Build image** — multi-arch, push to GHCR with `:sha` and `:latest` tags
8. **Load test smoke** — quick locust run, assert P95 hasn't regressed

### 9.2 `deploy-preview.yml` (new)

On every PR, deploy to a Fly.io preview app: `acrqa-pr-<NUM>.fly.dev`. Auto-comment on PR with the URL. Auto-tear-down when PR closes.

**This is the single most impressive thing you can do.** Reviewers (and your supervisor) get a live env to click through for every change.

### 9.3 `deploy-prod.yml` (new)

On merge to `main`:
1. Run alembic migrations against prod DB
2. Build production image
3. Deploy to Fly.io prod
4. Smoke test prod (`/health` returns 200, key endpoints respond)
5. Auto-rollback on smoke test failure
6. Slack/Discord notification on success/failure

### 9.4 Renovate bot

Drop `renovate.json` — automated dependency updates with PR-per-update. Shows you take supply-chain security seriously.

---

## 10. Security Hardening — Bonus Career Multiplier

You're building a security tool. Walking the talk is non-negotiable.

- **Secrets management:** Move from `.env` files to Doppler (free tier) or 1Password CLI for dev; Fly secrets / K8s secrets for prod. **Never** commit a `.env`.
- **Pre-commit:** Already have hooks; add `gitleaks` to scan staged files for secrets.
- **CSP headers:** API returns strict Content-Security-Policy, X-Frame-Options, etc.
- **Rate limit per IP** even for unauthenticated requests
- **Audit log:** Every admin action writes to `audit_log` table with actor, action, target, timestamp
- **Dependency pinning:** `requirements.txt` → `requirements.lock` (use `pip-compile`); Renovate keeps it fresh
- **SBOM in releases:** Every release artifact includes the SBOM as JSON
- **Sign Docker images:** Use cosign to sign images, document verification

---

## 11. The "If I Were You" Section

Read this if you read nothing else.

### What I would do FIRST (this week, before touching code):
1. Open a `docs/architecture/c2-containers.md` with a Mermaid diagram of the system **as it exists today.** This forces you to actually look at what you have. You'll find dead code, duplication, and weird coupling. Don't fix any of it — just see it.
2. Write `docs/adr/0001-context-and-goals.md` — one page on **what this project is for and what it isn't.** Pin the scope. This becomes the contract you hold yourself to.
3. Delete `scratch/` and any other obvious cruft (§3).
4. Sit down for one focused hour and write the README rewrite (§8.3). Future-you and future-recruiters thank you.

That's week 1. No new features. Just see, document, prune.

### What I would prioritize ruthlessly:

**Tier 1 — do these even if you're short on time** (highest career signal per hour):
- §5.3 Alembic migrations (3 days, makes you look like you know prod)
- §6.1 Real Dockerfile + §6.3 Terraform deploy (4 days, gives you a live URL)
- §7.1 Prometheus + Grafana (3 days, screenshots sell themselves)
- §8.1 C4 diagrams + §8.2 ADRs (1 week, ongoing — this is your interview cheat sheet)
- §9.2 PR preview deploys (2 days, the most impressive demo trick)

**Tier 2 — do these if you have a month or more:**
- §5.1 Flask → FastAPI
- §5.2 Celery
- §5.4 Auth
- §7.2 OpenTelemetry tracing
- §7.4–7.6 SLOs + runbooks + load tests

**Tier 3 — do these if you're going for senior-leaning roles:**
- §5.5 Webhooks / outbox
- §5.6 Multi-tenancy
- §6.2 Helm chart
- §6.4 Frontend rewrite
- §7.7 Chaos engineering

### What I would NOT do:
- **Don't start the Phase 2 TS rewrite yet.** Your roadmap mentions it. Until everything in this plan is done, the TS rewrite is procrastination dressed up as ambition.
- **Don't add a microservices split.** You have one service. Keep it that way until you have a reason. Premature distribution is the #1 anti-pattern in junior portfolio projects.
- **Don't build a billing/payments layer.** Looks fancy, learns you nothing relevant for a backend role, and adds compliance scope.
- **Don't add Kafka/NATS.** Redis pub/sub or the Postgres outbox pattern handles everything you need at this scale. Kafka in a portfolio project screams "I read a blog post."
- **Don't add machine learning beyond what you have.** AI explanation via Groq is the right amount. Don't fine-tune your own model. Don't add anomaly detection. Don't add "AI-powered" anything else. Stay focused.

### How I would pace it:

**12-week god-mode schedule (quarter-time student pace, ~15 hrs/week):**

| Week | Focus | Outcome |
|---|---|---|
| 1 | Cleanup + docs + diagrams | Clean repo, C4 diagrams, README rewrite |
| 2 | Alembic + settings + Dockerfile | Migrations + 12-factor + small image |
| 3 | FastAPI migration | Async API with OpenAPI auto-gen |
| 4 | Celery + auth | Background jobs + JWT/API keys |
| 5 | Webhooks + Helm | Event-driven + K8s manifests |
| 6 | Terraform + Prometheus | Live deploy + metrics |
| 7 | Tracing + SLOs + runbooks | Full observability stack |
| 8 | Load tests + chaos | Performance budget + resilience proof |
| 9 | Frontend rewrite (if time) | Modern SPA |
| 10 | CI/CD polish + preview deploys | Production-grade pipeline |
| 11 | Security hardening + SBOM | Supply chain story |
| 12 | Final polish + release v4.0.0 | Tagged release, blog post, talk slides |

If you only have 6 weeks: do weeks 1, 2, 3, 6, 7, 10. You'll be employable.

### How to know you're done:

You're done when you can answer **YES** to every question:

- [ ] Can a stranger run the project locally with one command?
- [ ] Is there a live URL anyone can hit right now?
- [ ] If I deleted the prod DB tomorrow, do I have a runbook to restore it?
- [ ] Can I show a Grafana screenshot of real traffic?
- [ ] Can I show a flame graph of a real scan?
- [ ] Do I have at least 5 ADRs?
- [ ] Does my CI deploy on every merge to main?
- [ ] Does every PR get its own preview URL?
- [ ] Have I tagged at least one major release with proper release notes?
- [ ] Can I explain in 60 seconds what this project does, in 5 minutes how it's architected, and in 30 minutes how I'd scale it 100x?

When all 10 are checked, write a blog post titled *"What I learned building ACR-QA"* and put it on dev.to / Hashnode / Medium. Link from your resume.

---

## 12. Anti-Patterns — Things That Look Impressive But Aren't

Career-poisoning mistakes I've seen students make:

| Anti-pattern | Why it's bad | What to do instead |
|---|---|---|
| Splitting into 5 microservices | You don't have the traffic to justify it; you'll spend all your time on inter-service plumbing | Stay monolithic with clean module boundaries; "you can split it later" is a real architectural property |
| Adding Kafka because "it's what FAANG uses" | Operationally heavy for one user | Postgres outbox + webhook delivery handles all event needs at this scale |
| Inventing your own auth | Even fintech doesn't do this | Use industry libs: `python-jose` for JWT, `passlib` for hashing |
| Writing your own ORM/query builder | Pure portfolio poison | SQLAlchemy 2.0 async, period |
| Hand-rolled CI scripts in Bash | Brittle, hard to read | GitHub Actions reusable workflows |
| "Service mesh" (Istio, Linkerd) | Not justified at < 10 services | Plain `Service` + `Ingress` is correct |
| GraphQL because REST is "boring" | REST + OpenAPI is more impressive than mediocre GraphQL | Master REST, learn GraphQL second |
| Custom container orchestration | You're competing with Kubernetes | Use K8s |
| "Real-time" everything via WebSockets | Most "real-time" needs are polling | Use polling + SSE for streaming; WebSockets only when bidirectional |
| Redis as a primary data store | Wrong tool | Postgres for state, Redis for cache+queue |

---

## 13. Final Word

You already built something good. The work above turns it into something **interview-winning**.

Pick **one** thing from §11 Tier 1 and start tomorrow. Don't read this again until that's shipped. Momentum > planning.

Then ship the next one. And the next.

The ones who build careers in backend/DevOps aren't the ones who plan the most. They're the ones who **operate what they built, in public, where everyone can see**.

Make your repo that public proof.

---

*Plan written 2026-05-05. Revisit and prune ruthlessly every 2 weeks. If a section feels aspirational and untouched after a month, delete it from the plan — the plan should match what you're actually doing.*
