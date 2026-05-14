# Changelog

All notable changes to ACR-QA are documented here.

## [v3.4.0] — Week 3: MCP Server + Embedding-Based Learned Suppression (May 14, 2026)

### Added — Feature 10: Learned Suppression v2 (CORE/engines/learned_suppression.py)

- **`LearnedSuppressionEngine`** — semantic FP suppression via `sentence-transformers` (`all-MiniLM-L6-v2`, 80MB, local, no API keys).
  - `suppress(findings, db)` → checks each finding's cosine similarity against previously-dismissed embeddings; confidence set to 0 if similarity ≥ 0.92
  - `store_dismissed(finding_id, db)` → embeds dismissed finding and stores in `finding_embeddings` table
  - `embed_text(text)` → returns JSON-serialisable float list via `SentenceTransformer.encode`
  - `is_available()` → graceful degradation if package not installed
  - `_cosine_similarity(a, b)` → pure-Python cosine similarity (no numpy required at runtime)
  - `_finding_to_text(finding)` → canonical text: `rule_id | message | file | line`
- **Alembic migration `0004`** — `finding_embeddings` table: `id`, `finding_id` (FK → findings.id ON DELETE CASCADE), `rule_id`, `code_context`, `embedding_json` (TEXT), `suppressed_at` (TIMESTAMPTZ)
- **DB methods** — `insert_finding_embedding`, `get_all_finding_embeddings`, `get_finding_embeddings_by_rule`, `delete_finding_embedding`
- **`TriageMemory.learn_from_fp`** — now also calls `LearnedSuppressionEngine().store_dismissed()` so every exact-match FP rule also gets an embedding stored for future similarity matching
- **Pipeline** — both `run()` and `run_js()` in `CORE/main.py` call `LearnedSuppressionEngine().suppress()` after exact-match triage memory, before deduplication; wrapped in `try/except` for graceful degradation

### Added — Feature 11: MCP Server (`acrqa-mcp/`)

- **`acrqa-mcp/server.py`** — `FastMCP` server exposing 3 tools:
  - `acrqa_scan(target_dir, repo_name)` — queues a Celery scan via `POST /v1/scans`, polls until complete, returns findings summary (count, severity breakdown, top 5)
  - `acrqa_explain(finding_id)` — retrieves AI explanation for a stored finding from `GET /v1/runs/findings/{id}/explanation`
  - `acrqa_fix(finding_id)` — retrieves autofix diff from `GET /v1/runs/findings/{id}/fix`
- **Config** — `ACRQA_URL` + `ACRQA_TOKEN` env vars, or `~/.config/acrqa/config.json`
- **`acrqa-mcp/pyproject.toml`** — packaged for `pip install acrqa-mcp`; entry point `acrqa-mcp` → `server:main`
- **Compatible with** Claude Code, Cursor, Continue — any MCP-capable AI coding agent

### Tests

- `TESTS/test_learned_suppression.py` — 35 tests: import, text repr, cosine similarity, embed mock, graceful degradation, semantic matching, store_dismissed, DB methods, migration, pipeline wiring
- `TESTS/test_mcp_server.py` — 35 tests: import, config, `_tool_scan` success/error/timeout/sorting, `_tool_explain` success/404/error, `_tool_fix` success/404/error, FastMCP tool registration, package structure
- `TESTS/test_god_mode.py` — +21 tests: `TestLearnedSuppressionGodMode` (12) + `TestMCPServerGodMode` (9)
- **Total: 1,864 passed, 0 failed, 85.82% coverage**
- **4 Alembic migrations** (baseline + users/api_keys + reachability + embeddings)

---

## [v3.3.2] — Week 2: Call Graph Reachability Engine (May 14, 2026)

### Added — Feature 9a: Call Graph Reachability (CORE/engines/reachability.py)

- **`CallGraphReachability`** — pure-AST static call graph engine. No runtime dependencies beyond stdlib `ast`.
  - `analyze(file_path)` → `CallGraphResult` with `reachable`, `unreachable`, `entry_points` sets
  - `enrich_findings(findings, target_dir)` — batch-enriches pipeline findings with per-file caching; looks up the containing function via `get_function_at_line()` and applies `-20` confidence penalty to dead-code findings
  - `apply_to_finding(file_path, function_name, finding)` — single-finding API
- **`get_function_at_line(source, line)`** — AST-based line-to-function mapper; returns innermost enclosing function or `None` for module-level code
- **Entry-point detection** — Flask/FastAPI routes (`@app.route`, `@router.get`, etc.), Celery tasks (`@app.task`, `@shared_task`), `__main__` blocks
- **BFS call graph traversal** — walks `ast.Call` nodes inside each `FunctionDef`; handles attribute calls (`self.helper()`)
- **Safe default** — library files with no detected entry points get `reachability_status: UNKNOWN`; confidence unchanged

### Added — Pipeline Integration (CORE/main.py)
- Reachability enrichment wired into both `run()` (Python pipeline) and `run_js()` after deduplication, before per-rule cap
- Persists `reachability_status` + `reachability_penalty` to DB on each `insert_finding()` call

### Added — Database (DATABASE/database.py + Alembic)
- `Database.update_finding_reachability(finding_id, status, penalty)` method
- Alembic migration `0003` (`20260514_0003_reachability_columns.py`) — adds `reachability_status VARCHAR(20)` and `reachability_penalty INTEGER` columns to `findings` table

### Tests
- **`TESTS/test_reachability.py`** — 74 tests covering `CallGraphResult`, `_detect_entry_points`, `_build_call_graph`, `get_function_at_line`, `enrich_findings`, `apply_to_finding`, all three fixture repos
- **`TESTS/test_integration_benchmarks.py`** — `TestReachabilityBenchmark` (6 tests): FP rate validated at **0%** across Flask/standalone/Celery fixtures
- **`TESTS/test_god_mode.py`** — `TestReachabilityGodMode` (12 tests): import, constants, all entry-point types, deep call chains, mutation safety, migration + DB method presence
- **Total: 1,773 tests passing, 85.73% coverage** (engine coverage: 91%)

---

## [v3.3.1] — Observability & Grafana Finalization (May 14, 2026)

### Fixed
- **Prometheus Metrics Generation**: Fixed a double-brace `{{` bug in the histogram metric generation inside `CORE/utils/metrics.py` that was causing Prometheus scrape formatting failures.
- **Histogram `_bucket` Suffix**: Fixed a bug where histogram buckets were emitted without the `_bucket` suffix when labels were present. This broke the `histogram_quantile()` PromQL calculations in Grafana for P95 latency.
- **Global Request Tracking**: The `@track_request` decorator was previously imported but never applied to routes, causing the `/metrics` endpoint to remain empty. Removed the redundant decorators and replaced them with global `@app.before_request` and `@app.after_request` hooks in `FRONTEND/app.py` to auto-track all HTTP traffic.
- **Grafana Datasource UID**: Fixed "Datasource not found" errors in the Grafana dashboard by explicitly pinning the `uid: prometheus` in `config/grafana/provisioning/datasources/prometheus.yml` to match the exported dashboard JSON.
- **Dashboard SLO Panels**: Updated the SLO availability and latency queries to use the `status_code` labels that are now correctly exported by the global request hooks. Also reduced timeline windows from `[30d]` and `[7d]` to `[5m]` so that fresh deployments can instantly visualize SLO adherence without waiting days for minimum scrape point requirements.

---

## [unreleased] — God Mode v2 + Phase 0/1/2 (May 5–6, 2026)

### Added — Phase 2 Test Infrastructure (May 6, 2026)
- **`TESTS/evaluation/ground_truth/{dvpwa,pygoat,dsvw,vulpy}.yml`** — ground truth moves from Python dicts in `scripts/run_evaluation.py` to versioned YAML. Each YAML declares `expected_findings` (with optional `out_of_scope` reason + rationale), `recall_target`, `precision_target`. Anyone can audit the thesis claims by reading these files.
- **`TESTS/evaluation/test_recall.py`** — Layer 5 evaluation harness. Runs ACR-QA via subprocess against each ground-truth YAML, computes recall on detectable categories, asserts ≥ target. Findings marked `out_of_scope` are excluded (documented gaps, not regressions). Includes a fast smoke variant on DSVW.
- **`TESTS/test_no_custom_rules.py`** — regression guard for the `CUSTOM-*` rule leak. Runs DSVW scan and asserts zero `CUSTOM-*` findings; CI fails if anyone adds a tool rule without mapping it. Phase 0 found 35 of these silently leaking.
- **`TESTS/test_celery_tasks.py`** — 9 tests against `CORE/tasks.py` (was 0% covered): registration, JSON-only serialization config, task-tracking config, success path (single-value + tuple return shapes), `None`/rate-limited path, exception re-raise, kwargs forwarding. Uses `.apply()` + in-memory result backend so tests run without Redis.
- **`pyproject.toml` markers** — registered `slow` (evaluation tests; skipped by default, run nightly via `-m slow`) and `integration` (live-services tests). Default `addopts` now `-m "not slow"` so the PR-fast suite stays under a minute.
- **Auto-cleanup fixture** in `test_recall.py` and `test_no_custom_rules.py` removes stale `DATA/outputs/<tool>.json` files before each scan to prevent the parallel-workspace race documented in PHASE_0_BASELINE.md §6.3.

### Phase 2 Surfaced
- **VulPy CWE-384 (weak session)** — pattern not implementable by Bandit / Semgrep-OSS (architectural, requires understanding session storage intent). Marked `out_of_scope: architectural_static_analysis_limit` in `vulpy.yml`. Same treatment as DVPWA's CSRF + YAML credentials.

### Test counts after Phase 2
- Default (PR-fast): **1,699 passed**, 13 skipped (was 1,690 — +9 Celery)
- Slow (nightly): 6 (4 recall battery + 1 smoke + 1 CUSTOM-* guard) — all pass
- Coverage: **85.65%** (was 84.85% — Celery moved from 0%)

### Added — Documentation & Strategy
- **`docs/GOD_MODE_PLAN.md` v2** — full rewrite. Drops CV-padding (Helm, Terraform, webhooks, multi-tenancy, TS rewrite) and bets on three competitive moats (reachability engine, MCP server, learned suppression) plus a blue-ocean wedge (proof-of-exploit + signed provenance attestations). Old plan archived at `docs/archive/GOD_MODE_PLAN_V1.md`.
- **`docs/GOD_MODE_PLAN.md` §9 Testing Strategy** — 6-layer testing pyramid for security tools. Coverage % is a tripwire, not a target. Ground truth must move to YAML; every thesis number must have a green test that generated it.
- **`docs/evaluation/PHASE_0_BASELINE.md`** — reality-check report from running ACR-QA on 6 real repos (DVPWA, Pygoat, VulPy, DSVW, Flask, httpx). Captures honest current numbers + 2 real bugs surfaced.

### Fixed — Phase 1 (May 6, 2026)
- **CUSTOM-* leakage closed** — added Ruff `UP012`/`UP028`/`UP045` to `RULE_MAPPING` (`normalizer.py`) and corresponding `STYLE-027`/`STYLE-028`/`STYLE-029` to `RULE_SEVERITY` (`severity_scorer.py`). DVPWA went from 8 unmapped findings to 0.
- **DVPWA ground truth corrected** (`scripts/run_evaluation.py`) — file paths fixed (e.g., `config.py` → `config/dev.yaml`), 3 categories now marked `out_of_scope` with explicit reasons (YAML not Python, Bandit B201 only covers Flask, CSRF requires runtime). Recall on Bandit-detectable categories: 3/3 = 100%.
- **`pipeline.run()` JSON output is now the FILTERED finding set** — previously `findings.json` contained the un-filtered raw normalizer output (1,536 entries on Flask); now it contains the deduped/capped/sorted final output (64 entries on Flask). Major correctness fix for all downstream consumers (autofix, post_pr_comments, generate_report, export_sarif).
- **`findings.json` per-PID writes** in `pipeline.run()` and `pipeline.run_js()` — partial mitigation for parallel-scan collisions. The deeper architectural collision (intermediate tool outputs `ruff.json`, `bandit.json`, etc. are also shared) is documented in `PHASE_0_BASELINE.md` §6.3 and deferred to a per-process workspace refactor.

### Cleanup
- Deleted `vscode-extension/` (26MB stub that called Flask `/api/analyze`; replaced by planned MCP server)
- Deleted dead Flask static files: `FRONTEND/static/dashboard.{html,css,js}`
- Deleted unused scripts: `scripts/benchmark_models.py`, `scripts/scale_benchmark.py`, `scripts/post_gitlab_comments.py`
- Pinned `redis==5.2.1` (was 7.1.0 — incompatible with `celery[redis]==5.4.0` upper bound `<6.0.0`)

### Documentation reorg
- Moved `AGENTS.md` → `docs/AGENTS.md`
- Moved `CODEBASE_INDEX.md` → `docs/CODEBASE_INDEX.md`
- Added `.claude/` and `coverage.xml` to `.gitignore`

---

## [v3.3.0] — FastAPI + Celery + Auth (May 5, 2026)

### Added — Async API (FastAPI)
- **`FRONTEND/api/main.py`** — FastAPI app running on port 8000 alongside legacy Flask (port 5000). All routes live under `/v1/`, Swagger UI at `/docs`, OpenAPI spec at `/openapi.json`.
- **Pydantic request/response models** (`FRONTEND/api/models.py`) — typed input validation and schema-generated OpenAPI docs for every endpoint.
- **Dependency injection** (`FRONTEND/api/deps.py`) — `get_db()`, `get_current_user()` (resolves JWT or API key), `require_role("admin")` RBAC decorator.
- **Three domain routers:**
  - `FRONTEND/api/routers/auth.py` — login, refresh, me, create-user (admin), API key CRUD
  - `FRONTEND/api/routers/runs.py` — runs list, findings, stats, PR summary, compliance, cost-benefit
  - `FRONTEND/api/routers/scans.py` — async scan dispatch, job status polling, single-file analysis, quick refresh, secrets, SCA, AI detection
- All Flask I/O operations wrapped in `asyncio.to_thread()` for non-blocking execution.

### Added — Background Jobs (Celery)
- **`CORE/tasks.py`** — Celery app configured with Redis as broker + result backend. `run_analysis_task` wraps `AnalysisPipeline.run()` as a background task.
- **`POST /v1/scans`** — returns `202 Accepted` with `{"job_id": "..."}` immediately (scan no longer blocks the request thread).
- **`GET /v1/scans/{job_id}`** — polls Celery result backend; maps `PENDING/STARTED/SUCCESS/FAILURE` → `queued/started/completed/failed`.
- **`docker-compose.yml`** — new `worker` service running `celery -A CORE.tasks worker --concurrency=4`.

### Added — Auth (JWT + API Keys + RBAC)
- **`users` table** — email, bcrypt password hash, role (admin/member/viewer), is_active.
- **`api_keys` table** — user FK, bcrypt key hash, name, scopes (JSON), last_used_at.
- **Alembic migration `0002`** — `users` + `api_keys` tables; reversible downgrade.
- **`POST /v1/auth/login`** — validates bcrypt hash, returns 15-min access token + 7-day refresh token (HS256 JWT).
- **`POST /v1/auth/refresh`** — validates refresh token, rotates both tokens.
- **`X-API-Key` header** — CI integrations authenticate with `acrqa_<random>` keys; only the bcrypt hash is stored.
- **`scripts/seed_admin.py`** — bootstraps first admin user via `ADMIN_EMAIL` / `ADMIN_PASSWORD` env vars.
- **`make seed-admin`** target.

### Added — Infrastructure
- **`docker-compose.yml`** — `api` service (FastAPI, port 8000) and `worker` service (Celery) using YAML anchors to share env/volumes with legacy `app` service.
- **`JWT_SECRET_KEY` env var** — must be set in production; falls back to a dev placeholder with warning.
- **`requirements.txt`** — added `fastapi==0.115.0`, `uvicorn[standard]==0.30.6`, `python-multipart==0.0.9`, `python-jose[cryptography]==3.3.0`, `passlib[bcrypt]==1.7.4`, `bcrypt==4.1.3`, `celery[redis]==5.4.0`, `pydantic-settings==2.3.4`.
- **`Makefile`** — added `make api` (uvicorn with --reload), `make worker` (celery), `make seed-admin`.

### Career signal coverage after v3.3.0
| Skill | Status |
|---|---|
| Async Python / FastAPI | ✅ |
| Message queues / Celery | ✅ |
| Database migrations / Alembic | ✅ |
| AuthN/AuthZ — JWT + API keys + RBAC | ✅ |
| Containers / Docker | ✅ |
| CI/CD depth | ✅ |
| Observability — metrics | ✅ |
| SRE practices / SLOs | ✅ |

---

## [v3.2.5] — CI/CD Overhaul & mypy Integration (May 5, 2026)

### Fixed — CI/CD
- **`acr-qa.yml` database init** — replaced `psql -f DATABASE/schema.sql` with `alembic upgrade head` in `analyze-pr` job (was missed when `tests.yml` was updated).
- **`acr-qa.yml` GROQ key rotation** — `analyze-pr` job now has all 4 `GROQ_API_KEY_*` secrets; previously only key 1 was set, breaking key rotation in auto-PR analysis.
- **`tj-actions/changed-files`** — bumped `v41 → v45`.
- **`deploy-preview.yml` permissions** — added `pull-requests: write` block; comment posting was failing with HTTP 403.
- **`tests.yml` coverage gate** — added `--cov-fail-under=40`; coverage was reported but never enforced.

### Added — CI/CD
- **Composite action** `.github/actions/acr-qa-setup` — extracts Python setup, Go tool install (with cache), and Alembic migration into a single reusable step shared by both `analyze-pr` and `manual-trigger` jobs. Go tools cached by version key, saving ~30s per run on cache hit.
- **mypy in CI** — added to `tests.yml` lint job (`mypy==1.11.0` + `types-PyYAML`, `types-requests`, `types-redis` stubs). Config in `pyproject.toml` `[tool.mypy]`; `CORE.main` and `scripts.*` suppressed with documented rationale.

### Fixed — Type Checking
- `scripts/test_gap_analyzer.py:146` — added `dict[str, set[str]]` annotation to `test_map` (mypy `var-annotated` error).
- `pyproject.toml` — added `[tool.mypy]` section with `ignore_missing_imports = true` and per-module overrides.

### Documented
- `CONTRIBUTING.md` — new "Type Checking (mypy)" section: how to run, what's covered, suppression table with rationale.
- `docs/TESTING_AND_CALIBRATION.md` — new CI Static Analysis Status table showing current pass/fail state of all 4 checks.

---

## [v3.2.5] — God Mode: Architecture Docs, Multi-Stage Docker, Alembic, SRE, Railway (May 5, 2026)

### Added — Documentation & Architecture
- **C4 Architecture diagrams** — 4 Mermaid diagrams covering all C4 levels (`docs/architecture/c1-context.md` through `c4-code.md`): system context, container map with port table, all internal components + pipeline sequence, single finding lifecycle from raw tool output to PostgreSQL.
- **5 Architecture Decision Records** in `docs/adr/`: ADR-0001 (thesis scope), ADR-0002 (LanguageAdapter ABC), ADR-0003 (RAG + semantic entropy), ADR-0004 (Groq + 4-key rotation), ADR-0005 (PostgreSQL 6-table schema).
- **README.md complete rewrite** — badges, 30-second pitch, inline C2 Mermaid diagram, 14-row competitive feature table, full CLI reference, thesis evaluation results.
- **SRE documentation** in `docs/sre/`:
  - `slos.md` — 4 formal SLOs (availability 99.5%/30d, P95 < 500ms/7d, scan completion 99%/7d, AI latency < 5s/7d) with error budget policy table.
  - 5 operational runbooks: `groq-api-down.md`, `high-error-rate-5xx.md`, `db-connection-pool-exhausted.md`, `disk-full-postgres.md`, `restore-from-backup.md`.

### Added — Infrastructure
- **Multi-stage Dockerfile** — `builder` stage (Python venv + pip), `go-tools` stage (gosec + staticcheck binaries via Go compiler), `runtime` stage (python:3.11-slim, non-root `acrqa` user, no build artifacts). OCI labels, `HEALTHCHECK` via `/api/health`.
- **Alembic database migrations** — `alembic.ini`, `alembic/env.py` (reads `DATABASE_URL` or `DB_*` env vars; normalizes Railway's `postgres://` to `postgresql://`), baseline migration `20260505_0001_baseline` covering all 6 tables with correct FK/index/cascade order.
- **Railway PR preview deploys** — `.github/workflows/deploy-preview.yml` creates a Railway environment per PR and tears it down on close. `railway.toml` runs `alembic upgrade head` before app start. `docs/setup/RAILWAY_DEPLOY.md` is the one-time setup guide.
- **Grafana SLO panels** (IDs 7-9) — API Availability 30d (stat, thresholds 99.0/99.5%), P95 Latency 7d (gauge, max 1000ms, threshold 500ms), Scan Completion Rate 7d (stat, thresholds 97/99%).

### Changed
- **CI (`tests.yml`)** — `alembic upgrade head` replaces raw `psql -f DATABASE/schema.sql` for database initialization.
- **`requirements.txt`** — Added `alembic==1.13.1`, `sqlalchemy==2.0.23`.
- **`Makefile`** — Added `db-migrate` and `db-rollback` targets.
- **`.gitignore`** — Added `test_targets/` and `scratch/`.
- **`docs/README.md`** — Added SRE, Deployment, and C4 Architecture sections.

### Removed
- **`scratch/`** — Deleted one-off debug scripts.

---

## [v3.2.4] — Quality Audit: CUSTOM-* Elimination, Severity Fix, JSON Output Clean

### Fixed
- **Go adapter — 0 CUSTOM-* on govwa:** Mapped 6 previously unmapped staticcheck rules (`S1023`, `S1025`, `S1031`, `S1039`, `ST1005`, `ST1006`) to canonical IDs `STYLE-021` through `STYLE-026` in `go_adapter.py` and `severity_scorer.py`.
- **JS adapter — 0 CUSTOM-eslint-unknown:** Extended null-ruleId filter in `normalize_eslint()` to suppress ESLint "Parsing error:" messages (CommonJS/ES6 import errors) that were generating `CUSTOM-eslint-unknown` as HIGH-severity findings (was 9 on dvblab).
- **severity_scorer.py duplicate keys:** Removed 15 duplicate `RULE_SEVERITY` dict entries (`F601` violations) that caused silent overrides due to Python dict last-value-wins semantics. Early HIGH-block duplicates removed; later more precise entries kept.
- **`SECURITY-047` invalid severity:** Changed from `"critical"` → `"high"`. `"critical"` is not a valid `CanonicalFinding` severity and would raise `ValueError` from Pydantic validator on any Python path that hit this rule.
- **`--json` stdout pollution:** Progress messages and shell script output were mixed with JSON on stdout. Logging now routes to `stderr` when `--json` is active; `run_checks.sh` stdout suppressed via `DEVNULL`. `--json` now outputs clean parseable JSON.
- **Go severity preservation:** `normalize_gosec()` previously let `SeverityScorer.score()` override native gosec severity (e.g., G401 HIGH → scored medium, G104 LOW → scored high). Fixed via `model_copy` restoring adapter-derived severity.
- **JS severity preservation:** Same issue in `normalize_eslint()` and `normalize_npm_audit()`. Fixed via `model_copy`. ESLint warnings now correctly stay "medium", not "low".

### Tests
- Updated 2 tests (`test_coverage_boost.py`, `test_normalizer_scorer.py`) that asserted `SECURITY-047` scored as `"critical"` → now assert `"high"`.
- All 1690 tests passing. 0 CUSTOM-* across all eval targets (pygoat, dvblab, govwa, dvpwa, dsvw, vulpy).

---

## [v3.2.4] — Logging Migration & System Stability

### Added
- **Production Logging:** Replaced 199 `print()` calls in production code (`CORE/`, `FRONTEND/`, `DATABASE/`) with proper structured logging (`logger.info()`, `logger.error()`).
- **Centralized Error Handling:** Added `@app.errorhandler(Exception)` to `FRONTEND/app.py` to capture all unhandled exceptions, log them with tracebacks via `app.logger.exception()`, and return standard 500 JSON responses.
- **Dependency Locking:** Generated definitive `requirements.lock` file.

### Changed
- **Testing Standard:** Switched to using `caplog` instead of `capsys` for validating log outputs in `TESTS/test_god_mode.py`.
- **Import Ordering:** Fixed E402 linter errors in `CORE/main.py` by reorganizing standard imports before `sys.path` changes.

### Removed
- **`traceback.print_exc()`:** Eliminated all direct traceback printing in the Flask app.
- **`test_comprehensive.sh`:** Deleted legacy script from project root.

---

## [v3.2.4] — Groq API Migration & KeyPool Load Balancing

### Added
- **Multi-Account KeyPool:** Implemented a round-robin rotation system across 4 Groq API accounts (`GROQ_API_KEY_1` to `GROQ_API_KEY_4`) to bypass rate-limit bottlenecks and increase throughput to ~120 requests/minute.
- **Model Upgrade:** Switched the explanation engine to `llama-3.3-70b-versatile` for enhanced reasoning and explanations.
- **Path Feasibility Engine:** Switched to `llama-3.1-8b-instant` for ultra-low latency routing validation.
- **Global Mocking:** Added a global `mock_env` fixture in `TESTS/conftest.py` to seamlessly inject dummy API keys for all test environments.

### Changed
- **API Provider:** Fully migrated from `groq-cloud-sdk` to `groq` SDK and native `httpx` for all LLM calls.
- **Dependencies:** Updated `requirements.txt` to remove Groq and pin `groq==1.2.0`.
- **CI/CD Configuration:** Updated `.github/workflows/acr-qa.yml` to utilize `GROQ_API_KEY_1` instead of legacy Groq tokens.
- **Lazy Imports:** `CORE/engines/__init__.py` no longer eagerly imports the LLM stack, preventing cascade failures when optional deps are missing.
- **Version Sync:** All version strings (`__init__.py`, `main.py`, `README.md`, `app.py`) now consistently say `3.2.4`.
- **Test Guard:** `test_eslint_config_generates_without_error` now skips gracefully when `npm` is not installed.

### Metrics
- **Total tests:** 1,689 (1 skipped due to npm absence)
- **Total coverage:** 87.03%
- **Overall precision:** 94.8%

---

## [v3.2.4] — God-Mode Coverage: Final Core & Flask App

### Added
- **`TESTS/test_code_extractor.py`** — 23 tests ensuring AST extraction robustness
- **`TESTS/test_pipeline_helpers.py`** — 45 tests for `main.py` deduplication, capping, and config filtering
- **`TESTS/test_flask_app.py`** — 107 tests simulating an entire client hitting `FRONTEND/app.py` REST APIs with DB mocks.
- **GitHub SARIF Integration** — Added `.github/workflows/acr-qa.yml` step to upload native findings to GitHub Security Tab.
- **GitHub Inline PR Suggestions** — Enhanced `scripts/post_pr_comments.py` to post `fix_code` blocks as one-click GitHub suggestions.
- **`ACRQA_NO_AI` environment flag** — Allows `run_evaluation.py` to execute locally without burning API quotas.
- **OWASP Go-SCP E2E Testing** — Successfully validated Go adapter against real-world vulnerabilities.
- **Thesis Evaluation Completion** — Generated full precision/recall numbers with 90% OWASP Top 10 coverage.

### Metrics
- **Total tests:** 1,699 (↑ +134 from v3.2.3)
- **Total coverage:** 79.24% (all core logic modules fully tested)
- `FRONTEND/app.py`: meaningful endpoint coverage
- `code_extractor.py`: 92% coverage

---

## [v3.2.3] — God-Mode Coverage: Metrics & Web Helpers

### Added
- **`TESTS/test_metrics_ratelimiter.py`** — 69 tests targeting system resilience wrappers
- `metrics.py`: cover full prometheus string generation, gauges, rate limits.
- `rate_limiter.py`: cover standard redis connectivity, decay mechanisms, and test graceful degradation.

### Metrics
- **Total tests:** 1,565 (↑ +69 from v3.2.2)
- `metrics.py`: 99% coverage
- `rate_limiter.py`: 84% coverage

---

## [v3.2.2] — God-Mode Coverage: explainer.py & autofix.py

### Added
- **`TESTS/test_explainer.py`** — 90+ tests for `ExplanationEngine` (11% → 93%)
  - Full Groq API mocking (sync + async httpx paths)
  - Redis cache hit/miss/error coverage
  - `_get_cache_key`, `_build_evidence_grounded_prompt`, `_ngram_similarity`, `_calculate_cost`
  - `get_fallback_explanation`, `self_evaluate_explanation`, `compute_semantic_entropy`
  - `generate_explanation_batch`, all exception/fallback branches
- **`TESTS/test_autofix.py`** — 70 tests for `AutoFixEngine` (0% → 96%)
  - Every fix method: unused imports, unused variables, f-string conversion, boolean comparison, type hints, bare except, eval, dead code
  - `apply_fixes`, `verify_fix`, `validate_fix` with full subprocess mocking
  - Timeout handling, bad JSON, missing file, out-of-range line edge cases

### Metrics
- **Total tests:** 1,496 (↑ +119 from v3.2.1)
- **Total coverage:** 73.65% (↑ from 66.64%)
- `explainer.py`: 11% → **93%**
- `autofix.py`: 0% → **96%**

---

## [v3.2.1] — God-Mode Coverage Push

### Added
- **`TESTS/test_batch1_pure_logic.py`** — 108 tests covering `quality_gate`, `config_loader`, `confidence_scorer`, `triage_memory`
- **`TESTS/test_batch2_engines.py`** — 96 tests covering `sca_scanner`, `cross_language_correlator`, `path_feasibility`
- **`TESTS/test_batch3_detectors.py`** — 100 tests covering `ai_code_detector`, `cbom_scanner`, `dependency_reachability`

### Coverage Gains (module-level)
| Module | Before | After |
|---|---|---|
| `quality_gate.py` | 0% | 95% |
| `config_loader.py` | 0% | 90%+ |
| `confidence_scorer.py` | 0% | 96% |
| `triage_memory.py` | 0% | 99% |
| `sca_scanner.py` | 0% | 88% |
| `cross_language_correlator.py` | 0% | 80% |
| `path_feasibility.py` | 0% | 88% |
| `ai_code_detector.py` | 0% | 90%+ |
| `cbom_scanner.py` | partial | 90%+ |
| `dependency_reachability.py` | 0% | 95% |

### Test count
1377 passed, 4 skipped — up from 1107 (v3.2.0) — **+270 tests**

### Coverage
**66.64% overall** — up from 63.33% (v3.2.0)

---

## [v3.2.0] — Feature 11: Go Language Support

### Added
- **`CORE/adapters/go_adapter.py`** — full Go language adapter (gosec + staticcheck + semgrep)
  - `gosec v2.18.2` integration: CWE-mapped findings, 26 rules mapped to ACR-QA canonical IDs
  - `staticcheck v0.4.3` integration: style, correctness, dead-code rules (19 mapped)
  - `semgrep` integration: fires only when `CORE/TOOLS/semgrep/go-rules.yml` is present (no network calls)
  - `detect_language()` static method for auto-routing
  - Deduplication by `(file, line, column, canonical_rule_id)`
- **`CORE/TOOLS/semgrep/go-rules.yml`** — 10 Go-specific Semgrep rules:
  - Command injection, SQL injection via `fmt.Sprintf`, hardcoded secrets,
    insecure TLS (`InsecureSkipVerify`), path traversal, weak random (`math/rand`),
    SSRF, reflected XSS, defer-in-loop, goroutine leak in HTTP handler
- **CLI `--lang go`** — added to `CORE/main.py` argument parser; routes to `GoAdapter`
- **Auto-detection** — `--lang auto` now falls back to Go detection after JS check
- **`TESTS/test_go_adapter.py`** — 51 unit tests: normalization, deduplication, rule mapping, category inference

### Fixed
- gosec line-range values (e.g., `"37-40"`) no longer crash `normalize_gosec`
- `semgrep` block no longer raises `UnboundLocalError` when local rules are absent

### Benchmark (GoVWA — known-vulnerable Go web app)
- **46 findings** — 14 medium, 32 low
- Top categories: weak crypto (MD5/SHA1), XSS template injection, SQL string formatting

### Test count
892 passed, 4 skipped — up from 526 (v3.1.3) — **+366 tests**

### Coverage
61.79% overall — above 40% CI threshold

---

## [v3.1.3] — Feature 10: Vulnerability Trend Dashboard + Feature 9 Cross-Language Correlator


### Added (Feature 10)
- Vulnerability trend dashboard — time-series view of findings across all historical scans
  - `GET /api/trends?limit=N&repo=name` — returns severity series, category series, confidence series, total series per run
  - `GET /api/repos` — returns list of repos with completed runs (for filter dropdown)
  - `Database.get_trend_data(limit, repo_name)` — enhanced with `avg_confidence`, `high_confidence_count`, `design_count`, `best_practice_count`, repo filter support
  - `Database.get_repos_with_runs()` — new method, excludes test- repos
  - Dashboard: 3 Chart.js charts (severity trend, confidence trend, category breakdown) with repo filter dropdown
- Fixed bug: `/api/trends` was reading `created_at` instead of `started_at` — all chart labels were "unknown"
- 8 new unit tests in `TESTS/test_new_engines.py::TestFeature10TrendDashboard` (all passing)

### Added (Feature 9 — committed separately)
- `CORE/engines/cross_language_correlator.py` — cross-language vulnerability correlator (CHARON approach)
- `CORE/engines/dependency_reachability.py` — npm dependency reachability checker
- Both wired into `AnalysisPipeline.run()` and `run_js()`

### Test count
526 passed, 4 skipped — up from 508 (v3.1.1)

### All 10 features complete
Features 1-10 fully implemented, tested, and documented at v3.1.3.

---

## [v3.1.2] — Feature 9: Cross-Language Vulnerability Correlator

### Added
- `CORE/engines/cross_language_correlator.py` — new `CrossLanguageCorrelator` engine
  - Inspired by CHARON (CISPA/NDSS) — cross-language vulnerability detection
  - Detects vulnerability chains spanning Python backend + Jinja2/HTML templates + JS frontend
  - 4 correlation types:
    - `SQLI_TO_TEMPLATE` — SQL injection in DAO, result rendered in template (confidence +20)
    - `TEMPLATE_INJECTION` — autoescape=False or |safe filter + backend security findings (confidence +15)
    - `XSS_CHAIN` — Python XSS finding + template unsafe output pattern (confidence +15)
    - `ROUTE_JS_CHAIN` — Python security finding + JS file in same feature directory (confidence +10)
  - `correlate(findings)` → list of CorrelationGroup objects
  - `enrich_findings(findings)` → tags findings with correlation metadata + boosts confidence scores
  - `scan_project()` → standalone scan using synthetic findings from regex patterns
  - Supports: aiohttp + aiohttp_jinja2, Flask + Jinja2, Django templates
- Wired into both `AnalysisPipeline.run()` and `run_js()` — runs before quality gate
- 10 new unit tests in `TESTS/test_new_engines.py::TestCrossLanguageCorrelator` (all passing)

### Verified on DVPWA
2 correlation groups detected:
- `[HIGH] SQLI_TO_TEMPLATE`: SQL injection in `dao/student.py` → `evaluate.jinja2`, `student.jinja2`, `index.jinja2`
- `[HIGH] TEMPLATE_INJECTION`: `autoescape=False` in `app.py` → all templates at XSS risk

### Academic citation
Implements cross-language vulnerability correlation inspired by **CHARON** (CISPA/NDSS) — detecting vulnerability chains that span multiple languages and layers in the same application.

### Test count
518 passed, 4 skipped — up from 508 (v3.1.1)

---

## [v3.1.1] — Feature 8: Dependency Reachability


### Added
- `CORE/engines/dependency_reachability.py` — new `DependencyReachabilityChecker` engine
  - Scans JS/TS source files for `require()` and `import` statements using regex
  - Classifies each vulnerable npm package as DIRECT / TRANSITIVE / UNKNOWN
  - DIRECT (penalty=0): package is explicitly imported in source — real risk
  - TRANSITIVE (penalty=-15): package installed but never directly imported — lower real risk
  - UNKNOWN (penalty=-5): not in package.json and not imported — likely false positive
  - `check(package_name)` → `ReachabilityResult` with level, penalty, import locations
  - `check_batch(packages)` → dict of results
  - `enrich_findings(findings)` → adds reachability metadata and adjusts confidence scores
  - Normalises scoped packages (`@org/pkg/subpath` → `@org/pkg`) and subpath imports
  - Excludes node_modules, dist, build directories from scanning
- Wired into `AnalysisPipeline.run_js()` — runs after CBoM scanner on every JS/TS scan
- Verified on NodeGoat: `ansi-regex` CVE correctly classified as UNKNOWN (never directly imported)
- 11 new unit tests in `TESTS/test_new_engines.py::TestDependencyReachability` (all passing)

### Test count
508 passed, 4 skipped — up from 497 (v3.1.0)

## [v3.1.0] — Feature 7: AI Path Feasibility Validator

### Added
- `CORE/engines/path_feasibility.py` — new `PathFeasibilityValidator` engine
  - Inspired by LLM4PFA (arXiv) — LLM-based path feasibility analysis for FP elimination
  - For HIGH/CRITICAL security findings only, runs a second async AI call asking: "Is this execution path actually reachable?"
  - Returns structured verdict: REACHABLE | UNREACHABLE | UNKNOWN
  - Confidence-weighted penalty system: UNREACHABLE+HIGH → -30, UNREACHABLE+MEDIUM → -20, UNKNOWN → -5
  - Runs inside the existing async httpx pipeline — no added sequential latency
  - `is_eligible(finding)` — only HIGH/CRITICAL security findings qualify (too expensive for medium/low)
  - `validate_async()` — single finding async check
  - `validate_batch_async()` — batch check for multiple findings
- `ExplanationEngine._explain_one_async()` — feasibility check wired after fix validation; adds `feasibility_verdict`, `feasibility_confidence`, `feasibility_reasoning`, `feasibility_latency_ms`, `feasibility_penalty`, `feasibility_checked` to every explanation result
- DB schema: 5 new columns on `llm_explanations` — `feasibility_verdict`, `feasibility_confidence`, `feasibility_reasoning`, `feasibility_latency_ms`, `feasibility_penalty`
- `Database.insert_explanation()` — now persists all feasibility fields
- 15 new unit tests in `TESTS/test_new_engines.py::TestPathFeasibility` (all passing)

### Academic citation
This feature implements the core idea from **LLM4PFA** (arXiv) — using LLMs to validate execution path feasibility and eliminate false positives in static analysis. ACR-QA applies this as a second-pass validator on HIGH severity security findings.

### Test count
497 passed, 4 skipped — up from 482 (v3.0.9)

---

## [v3.0.9] — Feature 6: Triage Memory

### Added
- `CORE/engines/triage_memory.py` — new `TriageMemory` engine
  - `learn_from_fp(finding_id, db)` — when user marks a finding as FP, extracts rule+file pattern and inserts a suppression rule into DB
  - `should_suppress(finding, db)` — checks if a finding matches any active suppression rule using fnmatch pattern matching
  - `suppress_findings(findings, db)` — filters a list of findings, removes suppressed ones, increments suppression counters
  - `get_active_rules(db)` — returns all active suppression rules
  - `_derive_pattern(file_path)` — derives a glob pattern from a file path (e.g. "tests/test_auth.py" → "tests/test_*.py")
- `suppression_rules` DB table — stores learned FP patterns: canonical_rule_id, file_pattern, created_from_finding_id, is_active, suppression_count
- `Database.insert_suppression_rule()` — inserts a new suppression rule
- `Database.get_suppression_rules(active_only)` — retrieves suppression rules
- `Database.increment_suppression_count(rule_id)` — tracks how many findings each rule has suppressed
- `AnalysisPipeline._apply_config_filters()` — now calls `suppress_findings()` after config filters (Python path)
- `AnalysisPipeline.run_js()` — now calls `suppress_findings()` after config filters (JS path)
- `FRONTEND/app.py` — `mark_false_positive` endpoint now calls `learn_from_fp()` automatically after storing feedback
- `GET /api/suppression-rules` — new endpoint returning all active suppression rules with suppression counts
- 8 new unit tests in `TESTS/test_new_engines.py::TestTriageMemory` (all passing)

### How it works
1. User marks finding as FP via dashboard or API
2. `learn_from_fp()` derives a file pattern and inserts a suppression rule
3. On next scan, `suppress_findings()` checks every finding against active rules
4. Matching findings are silently removed before AI explanation and DB insert
5. `suppression_count` tracks effectiveness over time

### Test count
482 passed, 4 skipped — up from 474 (v3.0.8)

---

## [v3.0.8] — Feature 5: Confidence Scoring

### Added
- `CORE/engines/confidence_scorer.py` — new `ConfidenceScorer` engine
  - Computes 0-100 integer confidence score per finding using 5 weighted signals:
    1. Severity — high=40, medium=25, low=10
    2. Category — security=20, design=10, best-practice=5, style=0
    3. Tool reliability — bandit/semgrep=15, eslint=10, ruff=8, vulture=5
    4. Rule specificity — known registry rule=10, CUSTOM-=5, unmapped=0
    5. Fix validated (Feature 1) — validated AI fix exists=10
  - `score(finding, fix_validated)` → integer 0-100
  - `score_batch(findings)` → list of scores
  - `label(score)` → "very high" / "high" / "medium" / "low" / "very low"
- `findings.confidence_score` — new INTEGER column (0-100) in DB, set at insert time
- `Database.insert_finding()` now calls `ConfidenceScorer` on every finding before DB insert
- `Database.get_findings()` and `get_findings_with_explanations()` return `confidence_score`
- `FRONTEND/app.py` — `_calculate_confidence()` uses DB-stored score first, falls back to heuristic for legacy findings
- Dashboard confidence slider — filters findings by minimum confidence threshold in real time
- 12 new unit tests in `TESTS/test_new_engines.py::TestConfidenceScorer` (all passing)

### Score examples (run 954)
| Finding | Tool | Score | Label |
|---------|------|-------|-------|
| SECURITY-001 + validated fix | bandit | 95 | very high |
| CUSTOM-sql-injection | semgrep | 85 | high |
| COMPLEXITY-001 | radon | 65 | medium |
| SOLID-001 | ruff | 53 | medium |
| STYLE-007 | ruff | 28 | very low |

### Test count
474 passed, 4 skipped — up from 462 (v3.0.7)

---

## [v3.0.7] — Feature 4: Autofix PR Bot

### Added
- `scripts/create_fix_pr.py` — fully rewritten autofix PR bot
  - Queries `get_validated_fixes()` from DB — only PRs fixes where `fix_validated=True` and `fix_code` is not null
  - Uses GitHub API blobs to commit file changes — no local file manipulation
  - Groups fixes by file, applies line-level patches sorted in reverse line order to preserve line numbers
  - Deletes any existing open autofix PR for the same run before creating a new one
  - Writes PR URL to `/tmp/acr_fix_pr_url.txt` for workflow summary
- DB schema extended: 4 new columns on `llm_explanations` — `fix_validated`, `fix_confidence`, `fix_code`, `fix_validation_note`
- `Database.insert_explanation()` now stores fix validation results from Feature 1's `validate_fix()`
- `Database.get_findings_with_explanations()` now returns fix fields
- `Database.get_validated_fixes(run_id)` — new method, returns only findings with validated AI fixes ready to apply
- `CORE/engines/explainer.py` — fixed missing `validated_fix` key in result dict (fix code was validated but not stored)
- GitHub Actions `acr-qa.yml` — new "Create Autofix PR" step runs after quality gate comment, before merge enforcement
- 3 new unit tests in `TESTS/test_new_engines.py::TestFeature4AutofixPR` (all passing)

### Fix validation chain
AI response → regex extract code block → validate_fix() → fix_validated + fix_code stored in DB
→ get_validated_fixes() → create_fix_pr.py → GitHub PR with only linter-verified fixes

### Test count
462 passed, 4 skipped — up from 459 (v3.0.6)

---

## [v3.0.6] — Architecture: Unified JS/TS Pipeline

### Changed
- Merged JS/TS CLI code path into `AnalysisPipeline.run_js()` — JS projects now go through the same 5-step pipeline as Python: rate limiting → tool execution → extra scanners (CBoM) → config filters → dedup → sort → AI explanations → quality gate → DB storage
- Removed duplicated pipeline logic from `main()` CLI function — JS routing is now a single `pipeline.run_js()` call
- JS findings now properly preserve categories from `_infer_category()` instead of being overwritten with `"security"` or `"style"`
- Fixed `_infer_category()` invalid category mappings: `"pattern"` → `"best-practice"`, `"imports"` → `"best-practice"`, `"async"` → `"best-practice"`, `"other"` → `"best-practice"`
- Added `clone_eval_repos.sh` — reproducible evaluation corpus setup script that pins DVNA to exact commit `9ba473a`

### Verified
- DVNA: 128 findings, 4 HIGH, 77 medium, 47 low — baseline stable ✅
- NodeGoat: 310 findings (319 − 9 deduped), 7 HIGH — first full pipeline run ✅
- AI explanations: 4 HIGH findings explained in 1292ms (DVNA), 7 in 2299ms (NodeGoat) ✅
- 459 tests passing, ruff clean ✅

---

## [v3.0.5] — Feature 3: Configurable Merge-Blocking Quality Gate

### Added
- `mode: block | warn` field in `.acrqa.yml` quality_gate section
  - `block` (default): gate failure exits CI with code 1 and prevents merge
  - `warn`: gate evaluates and posts comment but always allows merge (useful for onboarding new repos)
- `QualityGate.should_block(result)` — respects mode, returns False in warn mode even when thresholds exceeded
- `QualityGate.format_gate_comment(result)` — renders a markdown PR comment with severity table, per-check results, and merge verdict
- `scripts/post_gate_comment.py` — handles PR comment lifecycle (posting summary, deleting duplicates)
- 7 new configuration integration tests in `TESTS/test_new_engines.py`

### Changed
- GitHub workflow `.github/workflows/acr-qa.yml` updated to use the new script and post the quality gate summary to pending PRs
- `CORE/__init__.py` — Version bumped to `3.0.5`.

---

## [v3.0.4] — Feature 2: Cryptographic Bill of Materials (CBoM)

### Added
- `CORE/engines/cbom_scanner.py` — new `CBoMScanner` engine (226 lines, 86% test coverage)
  - Scans Python and JS/TS source files for cryptographic API usage using regex pattern matching (zero new dependencies)
  - Classifies every algorithm by quantum-safety status per NIST FIPS 203/204 PQC standards (2024):
    - 🔴 CRYPTO-001 (HIGH): Non-quantum-safe — MD5, SHA1, RSA, ECDSA, DES, RC4, DH, DSA
    - 🟡 CRYPTO-002 (MEDIUM): Classical-safe, not post-quantum-safe — SHA256, SHA512, AES-128, HMAC-SHA256, PBKDF2
    - 🟢 CRYPTO-003 (LOW): Quantum-resistant — SHA3, BLAKE2, AES-256, bcrypt, Argon2, ChaCha20
  - 28-entry algorithm registry with recommended post-quantum replacements (ML-KEM / ML-DSA)
  - Covers Python patterns: hashlib, hmac, pycryptodome, cryptography-lib, bcrypt, JWT
  - Covers JS/TS patterns: node:crypto, WebCrypto subtle API, bcrypt, JWT
  - Produces `CBoMReport` with inventory summary and per-usage `CryptoUsage` dataclass
  - Integrates with pipeline via `to_findings()` → canonical ACR-QA finding format
- Wired into `run_extra_scanners()` in `CORE/main.py` alongside secrets detector and SCA scanner
- Added `weak-hash-md5` cross-tool dedup group (`SECURITY-009` ↔ `CRYPTO-001`) to prevent double-reporting
- 7 new unit tests in `TESTS/test_new_engines.py::TestCBoMScanner` (all passing)

### Verified on real targets
| Target | Language | Files Scanned | Unsafe | Warn | Safe | Algorithms |
|--------|----------|--------------|--------|------|------|------------|
| `DATA/sandbox/acr-qa-bot-test` | JavaScript | 1 | 1 | 0 | 0 | MD5 |
| `TESTS/samples` | Python | 21 | 1 | 0 | 0 | MD5 |

### Detection example
[HIGH] MD5 @ server.js:30
code: crypto.createHash('md5').update(password).digest('hex')
fix:  SHA3-256 or BLAKE2b  (NIST FIPS 202 compliant)
[HIGH] MD5 @ auth_service.py:144
code: hashlib.md5(f"{password}{salt}".encode()).hexdigest()
fix:  SHA3-256 or BLAKE2b  (NIST FIPS 202 compliant)

---

## [v3.0.3] — 2026-04-14 (False Positive Rate Hardening)

### Added
- **`js-nosql-where-injection` rule** — New Semgrep rule catching MongoDB `$where` template
  literal injection (e.g. `{$where: \`this.userId == ${parsedUserId}\`}`). Fires correctly on
  NodeGoat's `allocations-dao.js:77`. Mapped to `SECURITY-058` in `JS_RULE_MAPPING`.
- **Round 7 — NodeGoat Evaluation** (`docs/evaluation/EVALUATION.md`) — 12 documented
  vulnerabilities cross-referenced. 50%+ adjusted recall (excluding logic/auth flaws
  that no static tool can catch).
- **Round 8 — FP Rate Analysis** — Three clean production codebases scanned post-refinement
  (Express, Koa, Fastify). Semgrep HIGH on Koa drops from 12 → **0** after test-file exclusions.
- **`docs/architecture/ARCHITECTURE.md` updated** — Added full JS/TS pipeline section,
  async AI engine details, PR bot integration, Redis caching.
- **`docs/TESTING_AND_CALIBRATION.md` Section 12** — Scale benchmark results and FP rate
  characterization data added.

### Changed
- **`js-eval-injection`** — Added `paths: exclude` block (`*.test.js`, `*.spec.js`,
  `test/**`, `tests/**`, `__tests__/**`). Eliminates false positives in framework test
  suites (Koa: 12 HIGH → 0).
- **`js-ssrf-request`** — Narrowed patterns to specific HTTP client libraries (axios, fetch,
  got, needle, superagent). Removed generic `request()`. Added same test-file exclusions.
- **`js-nosql-injection-mongodb`** — Narrowed to require `req.$X.$Y` or `req.body.$Y` as
  query value, preventing false positives on Sequelize ORM `.find()` calls.
- **`CORE/__init__.py`** — Version bumped to `3.0.3`.

### Fixed
- Koa scan was hanging due to slow `npm audit` on large dependency tree — Semgrep-only
  scan path used for precision measurement on clean codebases.
- NodeGoat NoSQL injection now correctly caught via new `$where` template literal pattern
  (was 0 finds; now 1 confirmed find at `allocations-dao.js:77`).

## [v3.0.2] — 2026-04-08 (EJS Scope Expansion & Eval Finalization)

### Added
- **EJS Template Support**: Expanded the JS/TS scan scope to include `.ejs` template files. Enabling Cross-Site Scripting (XSS) detection directly in template rendering logic.
- **Round 6 Benchmark Update**: DVNA ground-truth evaluation updated. Number of analyzed files increased (15 → 69) and total found issues after dedup increased correspondingly without sacrificing precision (1016 unique findings).

### Changed
- **Deduplication Engine**: Enhanced `get_all_findings()` to deduplicate findings based on exact `column` number along with file, line, and canonical rule id to significantly increase precision.
- **Test Suite**: Surpassed the 430 milestone. We now have 436 passing tests. Overall CORE module coverage is mapped back at 56%.
- `CORE/__init__.py`: Bumped core version from `3.0.1` to `3.0.2`.

## [v3.0.1-patch2] — 2026-04-07 (JS Adapter — CUSTOM-* Fix + Deduplication)

### Fixed
- **CUSTOM-* Semgrep mapping bug** (`js_adapter.py`): `normalize_semgrep_js` was delegating
  to `normalizer.normalize_semgrep` which uses Python `RULE_MAPPING`. JS rule IDs like
  `js-global-variable`, `js-console-log`, `js-command-injection` were all becoming
  `CUSTOM-*`. Fix: inlined normalization directly using `JS_RULE_MAPPING`.
- **Semgrep severity mapping**: Semgrep `ERROR`→`high`, `WARNING`→`medium`, `INFO`→`low`.
  Old path inherited Python normalizer's severity mapping which didn't handle Semgrep levels.

### Added
- **Deduplication in `get_all_findings()`**: removes findings with same `(file, line, canonical_rule_id)`
  from multiple tools. ESLint `no-var` (→ STYLE-017) + Semgrep `js-global-variable` (→ BEST-PRACTICE-004)
  are different rules and survive; exact duplicates are dropped. On DVNA: 946 raw → **112 unique**.
- **4 new tests** in `TestGetAllFindings` (`test_js_adapter.py`):
  - `test_normalize_semgrep_js_uses_js_rule_mapping`: asserts JS rules resolve via `JS_RULE_MAPPING`
  - `test_dedup_removes_same_file_line_rule_from_multiple_tools`
  - `test_dedup_preserves_same_rule_different_lines`
  - `test_empty_results_returns_empty` (already existed, confirmed passing)
- **Test count: 418 → 421 passing**
- **README badge**: 409 → **421 tests**
- **EVALUATION.md**: updated Round 6 results with post-dedup numbers (946 raw → 112 unique,
  834 duplicates removed), documented all 3 bug fixes, updated comparison table

## [v3.0.1-patch1] — 2026-04-05 (Beast Mode — Docs, Tests, DX)


### Added
- **E2E integration tests** (`TestE2EPipeline`, 4 tests): full mock pipeline through
  `get_all_findings()` — ESLint + npm audit + Semgrep, language field, tool_raw metadata
- **CLI routing tests** (`TestCLILanguageRouting`, 5 tests): `detect_language()`, adapter
  instantiation, `run_tools()` graceful error on empty dir, ESLint config generation
- **`EVALUATION.md` Round 6**: JS/TS adapter evaluation section — methodology, 16-category
  security coverage table, SonarQube CE comparison template + full runbook
- **Mermaid architecture diagram** in `ROADMAP.md`: current Python + JS pipeline → normalizer
  → gate → AI → DB → dashboard, plus Phase 2 TS rewrite components
- **README JS/TS section**: pipeline flow diagram, 15-rule security table, prerequisites
- **README CLI reference**: `--lang`, `--no-ai`, `--json`, `--version` flags + JS scan examples
- **Languages badge** on README: Python | JS | TS

### Changed
- `CORE/__init__.py`: version `3.0.0` → `3.0.1` (sync with CHANGELOG)
- README badges: 370 → **409 tests**, 2.9.0 → **3.0.1**, 123 → **299 rules**
- `.pre-commit-config.yaml`: added `--no-cov` to pytest hook (commits: 60s → ~2s)
- `pyproject.toml`: coverage threshold 30% → **40%**
- Test count: **409 → 418 passing** (9 new JS E2E + CLI routing tests)
- Roadmap: JS adapter checkbox checked ~~(v3.0.1)~~

## [v3.0.1] — 2026-04-05 (JavaScript/TypeScript Support)


### Added
- **`CORE/adapters/js_adapter.py`** — Full JS/TS language adapter:
  - ESLint runner with `eslint-plugin-security` (20 rules, auto-config via temp JSON)
  - Semgrep JS runner using `TOOLS/semgrep/js-rules.yml`
  - `npm audit` SCA runner — maps CVEs to `SECURITY-059`/`SECURITY-060`
  - `normalize_eslint()`, `normalize_npm_audit()`, `normalize_semgrep_js()` → CanonicalFinding
  - `detect_language()` — auto-detects python/javascript/mixed from project structure
  - `node_modules`, `dist`, `build`, `.next` automatically excluded
- **`TOOLS/semgrep/js-rules.yml`** — 15 custom Semgrep JS/TS security rules:
  eval injection, SQL injection, NoSQL injection, XSS (innerHTML + document.write),
  prototype pollution, path traversal, open redirect, hardcoded secrets,
  insecure Math.random(), JWT none algorithm, command injection, console.log, var usage
- **`--lang` CLI flag** — `auto` (default), `python`, `javascript`, `typescript`.
  Auto-detection routes to `JavaScriptAdapter` when `package.json` + JS files found.
- **`docs/ROADMAP.md`** — Full project roadmap: Phase 1 (Python), Phase 1B (JS adapter),
  Phase 2 (TS rewrite plan with architecture, stack, implementation order, migration guide).
- **`TESTS/test_js_adapter.py`** — 39 new tests covering all adapter functionality.

### Changed
- `severity_scorer.py`: 20 new JS canonical IDs — `SECURITY-051..060`, `STYLE-017/018`,
  `ASYNC-002/003`, `VAR-002`, `PATTERN-002`, `BEST-PRACTICE-007`, `IMPORT-004`
- Test count: **370 → 409 passing** (39 new JS adapter tests)

### How to scan JS/TS projects
```bash
python -m CORE --target-dir /path/to/react-app          # auto-detects JS
python -m CORE --target-dir /path/to/express-app --lang javascript --no-ai
python -m CORE --target-dir /path/to/next-app --json > findings.json
```

## [v3.0.0] — 2026-04-05 (Python Version Finalized)

### Added
- **`docs/API_REFERENCE.md`** — Full REST API reference for all 22 endpoints, CLI reference, and JS integration example. Stable surface for any JS frontend, VS Code extension, or CI tool.
- **CLI: `--version`** — `python -m CORE --version` prints `ACR-QA v3.0.0`
- **CLI: `--no-ai`** — Skips AI explanation step entirely (sets limit=0). Useful for CI pipelines or large repos where speed matters.
- **CLI: `--json`** — Dumps findings as JSON to stdout after analysis (pipe-friendly for JS consumers: `python -m CORE --json > results.json`)
- **12 new `RULE_MAPPING` entries** (Round 5 calibration): `UP041`, `B027`, `UP030`, `B011`, `B018`, `B023`, `B026`, `B009` (Ruff bugbear), plus `sql-injection-string-concat`, `global-variable`, `open-without-context-manager`, `path-traversal` (Semgrep). CUSTOM-* count is now 0 across all tested repos.
- **Round 5 repo testing**: Django, SQLAlchemy, aiohttp, black, Pillow — 5 new repos benchmarked.

### Changed
- **Version** unified to `v3.0.0` across `CORE/__init__.py` and `CORE/main.py` (was v2.7.0 vs v2.9 inconsistency)
- **`SECURITY-049`** = path-traversal (high), **`SECURITY-050`** = B023 closure bug (medium)
- **`BEST-PRACTICE-005`** = `open()` without context manager (medium — resource leak)
- **`BEST-PRACTICE-006`** = `getattr()` with constant string attribute (low)
- `main.py` argument parser adds usage examples in `--help` epilog
- `TESTING_AND_CALIBRATION.md` Section 11 added with Round 5 full analysis

### Notable Findings (Round 5)
| Repo | Gate | Notes |
|------|------|-------|
| aiohttp | ✅ PASS | 0 HIGH — exactly as expected for a strictly-maintained async lib |
| Django | ❌ FAIL | B324 hashlib FPs (intentional MD5 for cache/legacy — known limitation) |
| SQLAlchemy | ❌ FAIL | Same B324 FPs |
| black | ❌ FAIL | 2 HIGH (B023 closure bugs — real issues) |
| Pillow | ❌ FAIL | 3 HIGH (path-traversal in format loaders — real concerns) |

### Commits
| SHA | Summary |
|-----|---------|
| `5bda20b` | feat(rules): Round 5 testing — 12 new CUSTOM-* rules mapped |
| `b213a1c` | chore: pre-commit hooks, AGENTS.md, CODEBASE_INDEX.md, mypy clean |

## [v2.9] — 2026-03-31 (God Mode Validation & Coverage Overhaul)

### Added
- **77 coverage-boost tests** — `TESTS/test_coverage_boost.py` targeting `quality_gate.py` (8%→93%) and `severity_scorer.py` (34%→62%). Covers all CUSTOM-* keyword inference, COMPLEXITY/DEAD/DUP context adjustments, message-parsing fallbacks, and the `score_severity()` convenience function.
- **Thesis deliverables** — `docs/evaluation/USER_STUDY_PROTOCOL.md` (20-min study protocol), `USER_STUDY_SURVEY.md` (15-question questionnaire), `user_study_responses_template.csv`, and `docs/DEMO_VIDEO_SCRIPT.md` (structured 5-minute recording script).
- **KB entries** for `NAMING-003`, `IMPORT-003`, `STYLE-005` in `config/rules.yml` — richer AI explanations for previously unmapped rules.

### Changed
- **Version** unified to `v2.7.0` across `CORE/__init__.py` and `main.py` (was v2.5/v2.6 inconsistency)
- **Severity upgrades** — `SECURITY-008` (pickle/marshal) and `SECURITY-018` (yaml.load unsafe) promoted from **medium → high** to reflect CWE-502 arbitrary code execution risk
- **CUSTOM-* findings eliminated** — `N813→NAMING-003`, `F405→IMPORT-003`, `UP036→STYLE-005` added to `RULE_MAPPING` in `normalizer.py`; output now shows 0 `CUSTOM-*` findings
- **PR comment paths** — `clean_file_path()` added to `post_pr_comments.py` strips `/tmp/pr-files/` and runner checkout paths so comments show `myapp/login.py:38` not `/tmp/pr-files/myapp/login.py:38`
- **Semgrep FP reduction** — `assert-for-validation` rule now excludes `tests/`, `conftest.py`, and framework-internal paths via `paths.exclude`

### Fixed
- Test assertion for `SECURITY-008` moved from `test_medium_security_rules` to `test_all_security_rules_are_high` to match intentional severity upgrade

### Commits
| SHA | Summary |
|-----|---------|
| `10669e8` | test: 77 coverage-boost tests for quality_gate + severity_scorer |
| `327dd74` | docs: user study materials + demo video script |
| `dfe8288` | test: SECURITY-008/018 assertions updated (medium→high) |
| `edf7adf` | fix: complete code quality overhaul v2.7.0 |
| `e0686d5` | fix: god-mode deep analysis fixes |
| `eca9355` | fix: add missing Semgrep rule mappings |

---

## [v2.7] — 2026-03-05 (Competitive Features Release)

### Added
- **OWASP Top 10 Compliance Report** — `scripts/generate_compliance_report.py` maps all security findings to OWASP (2021) categories + CWE IDs, generates markdown or JSON reports
- **Test Gap Analyzer** — `scripts/test_gap_analyzer.py` finds untested functions/classes via AST parsing with quality gate integration (no competitor does this)
- **Feedback-Driven Severity Tuner** — `scripts/feedback_tuner.py` analyzes stored false-positive feedback to compute per-rule FP rates and auto-generate `config/severity_overrides.yml`
- **Config Validator & Template Generator** — `scripts/validate_config.py` validates `.acrqa.yml` against a schema, catches errors before silent failures, and generates documented config templates
- **Policy Engine Documentation** — `docs/POLICY_ENGINE.md` documents the policy-as-code system
- **Confidence-Based Noise Control** — `?min_confidence=0.7` filter on `/api/runs/<run_id>/findings` suppresses low-confidence findings (addresses #1 developer complaint)
- **`_calculate_confidence()` scoring function** — factors: rule citation in explanation, severity level, security category, explanation presence
- **3 new API endpoints** — `/api/runs/<run_id>/compliance`, `/api/test-gaps`, `/api/policy`
- **God-Mode Test Suite** — `TESTS/test_god_mode.py` with 78 tests across 11 classes covering all new/old features, edge cases, and cross-feature integration
- **Total test count** — 97 → 273 tests (273 passed, 4 skipped in 5.97s)

### Changed
- **README.md** — updated badges (v2.7, 273 tests), added 4 new differentiators, 2 new feature sections (Test Gap Analyzer + Policy-as-Code), architecture diagram, project structure (4 new scripts, 2 new test files), industry parity table (+6 rows), docs table (+3 entries), Phase 2 roadmap (completed items checked)
- **TESTING_REPORT.md** — updated to v2.7 with god-mode test matrix and cross-feature integration results

### Fixed
- **Version consistency** — all scripts (`export_sarif.py`, `post_pr_comments.py`, `generate_pr_summary.py`) now use `CORE.__version__` instead of hardcoded version strings
- **`auto_fixable_rules` was missing 2 rules** — added `SECURITY-027` (SQL injection) and `DEAD-001` (dead code removal) to `generate_pr_summary.py`
- **Flask secret key hardened** — replaced hardcoded `"dev-secret-key-change-in-production"` with `os.urandom(32).hex()` fallback
- **SARIF `informationUri`** — updated from placeholder to actual repo URL

## [v2.6] — 2026-03-05 (Deep-Code Audit & Coverage Push)

### Added
- **98 new tests** — `TESTS/test_deep_coverage.py` covering 12 components end-to-end (SeverityScorer, AutoFix, SecretsDetector, AICodeDetector, CodeExtractor, Normalizer, ConfigLoader, QualityGate, PythonAdapter, Flask API, Database CRUD, Metrics)
- **Branch coverage push** — 28% → 53% (+25pp across the board)
- **TESTING_REPORT.md** — full deep-code testing report with per-module coverage breakdown

### Fixed
- **Flask 500 → 404** — `/api/findings/{id}/mark-false-positive` and `/api/findings/{id}/feedback` now return 404 for nonexistent findings instead of crashing with a PostgreSQL FK constraint error
- **Inline suppression was broken** — `normalize_all()` referenced `finding.file_path` / `finding.line_number` but `CanonicalFinding` uses `finding.file` / `finding.line` — `# acr-qa:ignore` comments never actually worked
- **Normalizer double-parsed Ruff** — `normalize_ruff()` called twice per run (once for data, once for print count), wasting CPU and creating duplicate objects
- **Database NULL `rule_id` crash** — `insert_finding()` could insert NULL into the NOT NULL `rule_id` column when findings lacked the key; now uses or-chained fallbacks
- **4 bare `except:` in severity_scorer.py** — replaced with `except Exception:` to avoid catching SystemExit/KeyboardInterrupt
- **Dead expression in `verify_fix()`** — `fix_result.get("original", "")` return value was silently discarded

### Removed
- **Dead `SEVERITY_MAPPING` dict** — declared in `normalizer.py` but never used anywhere
- **18 trailing whitespace errors** — cleaned across 6 files (`database.py`, `app.py`, `config_loader.py`, `compute_metrics.py`, `generate_pr_summary.py`, `user_study.py`)

## [v2.5] — 2026-03-04 (Strategic Audit Fixes)

### Added
- **Rich terminal UI** — `--rich` flag for beautiful color-coded findings tables and quality gate panels
- **27 security rules** — SECURITY-003 through SECURITY-033 added to `rules.yml` (Bandit-mapped)
- **Prometheus `/metrics` endpoint** — now registered in Flask dashboard (was built but never activated)

### Changed
- **RAG rule coverage** — 43% → 100% (all 47 normalizer rules now have rules.yml entries)
- **Pipeline version** — v2.4 → v2.5
- **README** — updated CLI docs (--rich), test count (97), RAG coverage (66 rules)

### Fixed
- Duplicate `/metrics` endpoint registration that caused test failures
- `.vulture_whitelist.py` moved from project root to `config/` for cleanliness

## [v1.0] — 2026-03-04 (Python Stage Complete)

### Tag: `v1.0-python-complete`

### Added
- **Quality Gates** — configurable severity thresholds (max_high, max_medium, max_total, max_security) that fail CI with exit code 1
- **Per-repo configuration** — `.acrqa.yml` for rule enable/disable, severity override, path ignore, quality gate thresholds
- **Inline suppression** — `# acr-qa:ignore` (blanket) and `# acrqa:disable RULE-ID` (per-rule)
- **Finding deduplication** — cross-tool dedup by file+line+rule with tool priority (security > specialized > general)
- **Adapter architecture** — `LanguageAdapter` abstract base → `PythonAdapter` + `JavaScriptAdapter` placeholder
- **23 new tests** — 12 ConfigLoader + 11 QualityGate (97 total)
- **PERFORMANCE_BASELINE.md** — real pipeline timing measurements
- **`.env.example`** — environment variable template for onboarding
- **`make init-config`** — generates default `.acrqa.yml`
- **LICENSE** (MIT)
- **CHANGELOG.md** (this file)
- **CONTRIBUTING.md**

### Changed
- **`main.py`** — major rewrite: ConfigLoader integration, dedup, quality gate, config filters, exit codes
- **`normalizer.py`** — added inline suppression filtering in `normalize_all()`
- **`Makefile`** — added `init-config` target, wired into setup chain
- **`README.md`** — updated test count (77→97), doc links, 4 new features in industry table
- **`.gitignore`** — added node_modules, .ruff_cache, build artifacts
- **`.dockerignore`** — added TESTS/, node_modules, vscode-extension, build artifacts
- **`.github/workflows/acr-qa.yml`** — added `set -o pipefail`, quality gate enforcement step
- **`requirements.txt`** — pinned all dependencies to exact versions, added httpx + prometheus-client

### Removed
- `docker-run.sh` / `docker-dashboard.sh` (obsolete)
- `vscode-extension/node_modules/` from git tracking (26MB saved)
- `outputs/` directory at root (redundant with `DATA/outputs/`)

### Fixed
- ConfigLoader was dead code — never imported in main.py
- Pipeline always exited 0 — CI never blocked bad code
- GitHub Actions `tee` swallowed exit codes — quality gate failures were silent

### Reorganized
- `docs/` consolidated: DOCS/ + real-docs/ + project-docs/ + diagrams/ + images/ → architecture/ + setup/ + thesis/ + media/ + assignments/

---

## [v0.9] — 2026-01-28 (Phase 1 + Phase 2 Features)

### Added
- Bandit security scanner (6th tool)
- Source citations in reports (`[RULE-ID](config/rules.yml)`)
- Autofix suggestions with code examples
- Expanded knowledge base (10 → 32 rules)
- Confidence scores (0.6-0.9 based on rule citation)
- Response caching (Redis, 7-day TTL)
- GitLab CI/CD integration + MR comments
- Issue grouping API endpoint
- OWASP/SANS compliance reporting
- GitHub Actions CI/CD workflow
- PR summary generator
- Quick stats API
- Fix confidence API
- Secrets detector engine
- SCA scanner (pip-audit)
- AI-generated code detector
- Extended autofix (8 fix types)
- Rate limiting (token bucket + Redis)
- Pydantic v2 schema validation

### Fixed
- Ruff detection bug (exit code 1 overwrote output with `[]`)
- Bandit detection bug (same issue)
- Pydantic deprecation warnings

---

## [v0.1] — 2025-11-24 (MVP)

### Added
- 5 detection tools (Ruff, Semgrep, Vulture, jscpd, Radon)
- Canonical findings schema
- RAG-enhanced AI explanations (Groq)
- PostgreSQL provenance database
- Flask dashboard
- Basic analysis pipeline
