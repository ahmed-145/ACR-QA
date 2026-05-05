# Contributing to ACR-QA

Thank you for your interest in contributing to ACR-QA! This document explains how to set up your development environment and submit changes.

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/ahmed-145/ACR-QA.git
cd ACR-QA

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment
cp .env.example .env
# Edit .env with your GROQ_API_KEY_1..4, DB credentials, and JWT_SECRET_KEY

# 5. Start the stack (PostgreSQL + Redis + Flask + FastAPI + Celery worker + Prometheus + Grafana)
make up

# 6. Run database migrations (creates all tables including users + api_keys)
make db-migrate

# 7. Seed the first admin user
make seed-admin

# 8. Generate default config
make init-config

# 8. Run tests
pytest TESTS/ -v
```

## Project Structure

```
CORE/                → Engine logic (normalizer, explainer, quality gate, etc.)
CORE/adapters/       → Language adapters (Python, JavaScript/TypeScript, Go)
CORE/tasks.py        → Celery task definitions (background scan worker)
DATABASE/            → PostgreSQL ORM and connection layer
FRONTEND/app.py      → Flask dashboard (22 endpoints, port 5000 — legacy)
FRONTEND/api/        → FastAPI v1 REST API (port 8000, async, OpenAPI docs at /docs)
FRONTEND/auth/       → JWT + API key utilities (jwt_utils.py, api_key_utils.py)
TESTS/               → pytest suite (1,690 tests)
TOOLS/               → Shell scripts for running analysis tools
scripts/             → CI/CD and utility scripts (seed_admin.py, etc.)
config/              → Prometheus, Grafana dashboards, and rule definitions
alembic/             → Database migration scripts (Alembic)
docs/                → Architecture docs, ADRs, SRE runbooks, setup guides
docs/adr/            → Architecture Decision Records (0001–0005)
docs/sre/            → SLOs and operational runbooks
```

## Development Workflow

1. **Create a branch** from `main`
2. **Make your changes** following the existing patterns
3. **Add tests** for new functionality in `TESTS/`
4. **Run the test suite** — all 1,690 tests must pass:
   ```bash
   .venv/bin/pytest TESTS/ -q
   ```
5. **Run the pipeline** to verify integration:
   ```bash
   python3 CORE/main.py --target-dir TESTS/samples/comprehensive-issues --limit 3
   ```
6. **Submit a PR** — the ACR-QA GitHub Action will analyze your code and Railway will deploy a preview environment automatically.

## Database Migrations

All schema changes go through Alembic. **Never edit `DATABASE/schema.sql` directly** — it is kept only as a reference.

```bash
# Apply all pending migrations
make db-migrate

# Roll back the last migration
make db-rollback

# Create a new migration after changing the schema
.venv/bin/alembic revision --autogenerate -m "add user_id to analysis_runs"

# On a fresh database, stamp the baseline (existing DB) or upgrade (new DB)
.venv/bin/alembic stamp 0001      # existing DB with tables already created
.venv/bin/alembic upgrade head    # new empty DB
```

## Adding a New Language Adapter

To add support for a new language (e.g., JavaScript, Java):

1. Create `CORE/adapters/<language>_adapter.py`
2. Implement the `LanguageAdapter` interface from `CORE/adapters/base.py`
3. Add tool runner script in `TOOLS/run_<language>_checks.sh`
4. Add rule mappings to `CORE/engines/normalizer.py`
5. Add rule definitions to `config/rules.yml`
6. Add tests in `TESTS/test_<language>_adapter.py`
7. Add test samples in `TESTS/samples/<language>-issues/`

See `CORE/adapters/python_adapter.py` for a reference implementation.

## Running the FastAPI Server

The async API runs on port 8000 alongside the legacy Flask dashboard (port 5000).

```bash
# Dev mode (auto-reload)
make api
# → uvicorn FRONTEND.api.main:app --host 0.0.0.0 --port 8000 --reload
# → Swagger UI: http://localhost:8000/docs
# → OpenAPI JSON: http://localhost:8000/openapi.json
```

All v1 endpoints require authentication. Authenticate first:
```bash
# Seed an admin user (first time only)
make seed-admin

# Get a JWT token
curl -s -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@acrqa.local","password":"changeme123!"}' | jq .access_token
```

Use `Authorization: Bearer <token>` or `X-API-Key: acrqa_<key>` on all `/v1/` requests.

## Running the Celery Worker

Scans submitted via `POST /v1/scans` are queued and run by the Celery worker. Redis must be running.

```bash
make worker
# → celery -A CORE.tasks worker --loglevel=info --concurrency=4

# Submit a scan and poll for status:
JOB=$(curl -s -X POST http://localhost:8000/v1/scans \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"target_dir":"TESTS/samples/comprehensive-issues","repo_name":"test"}' | jq -r .job_id)

curl http://localhost:8000/v1/scans/$JOB -H "Authorization: Bearer $TOKEN"
```

## Adding New v1 API Endpoints

1. Add request/response Pydantic models to `FRONTEND/api/models.py`
2. Add the route to the relevant router (`FRONTEND/api/routers/runs.py`, `scans.py`, or `auth.py`)
3. All routes require `user: dict = Depends(get_current_user)` — omit only for public endpoints
4. Use `asyncio.to_thread()` for any blocking DB or subprocess calls

## Adding New Rules

1. Define the rule in `config/rules.yml` with: name, category, severity, description, rationale, remediation, examples
2. Add the rule mapping in `CORE/engines/normalizer.py` → `RULE_MAPPING` dict
3. Ensure the underlying tool (Ruff, Semgrep, etc.) detects it

## Code Style

- Python 3.11+
- Use type hints where practical
- Follow existing patterns in the codebase
- Run `ruff format` before committing

## Type Checking (mypy)

mypy runs in CI on every push (lint job). To run locally:

```bash
pip install mypy types-PyYAML types-requests types-redis
mypy CORE/ DATABASE/ FRONTEND/
```

Configuration lives in `pyproject.toml` under `[tool.mypy]`. Four modules are currently suppressed with `ignore_errors = true`:

| Module | Reason |
|--------|--------|
| `CORE.main` | Pre-existing `Mapping[str, Any]` vs `dict` type conflicts in the pipeline orchestrator. Requires auditing all engine function signatures to fix properly — tracked as future work. |
| `scripts.*` | Utility scripts not part of the importable library; type-checking them is not required. |
| `FRONTEND.api.*` | FastAPI dependency injection uses runtime-evaluated annotations that mypy cannot resolve without `--explicit-package-bases`. Auth and API code is covered by functional tests instead. |
| `FRONTEND.auth.*` | Same reason as above — passlib and jose stubs are incomplete. |

If you add new code to `CORE/` or `DATABASE/`, it **will** be type-checked. Add annotations to new functions. Do not extend the suppression list without a comment explaining why.

If you add new code to `CORE/` (engines, adapters, utils), it **will** be type-checked. Add annotations to new functions. Do not extend the suppression list without a comment explaining why.

## Configuration

Per-repo configuration is via `.acrqa.yml`. See the generated default for all options:
```bash
make init-config
```

## Inline Suppression

Suppress specific findings with inline comments:
```python
password = "admin123"  # acr-qa:ignore
eval(user_input)       # acrqa:disable SECURITY-001
```

## Questions?

Open an [issue on GitHub](https://github.com/ahmed-145/ACR-QA/issues).
