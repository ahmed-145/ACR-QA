# AGENTS.md
# Universal AI agent instructions for ACR-QA.
# Any AI tool (Claude Code, Copilot, Cursor, Windsurf, etc.) should read this before touching code.
# For deeper project memory and gotchas, read AGENT_NOTES.md (gitignored, local only).

> **Strategic plan:** `docs/GOD_MODE_PLAN.md` (v2 rewritten 2026-05-05). Phase 0 baseline: `docs/evaluation/PHASE_0_BASELINE.md`. Plan v1 archived at `docs/archive/GOD_MODE_PLAN_V1.md`.

---

## Project

**ACR-QA** — Automated Code Review & Quality Assurance
Graduation thesis project for Ahmed at KSIU. Supervisor: Dr. Samy.
**Version:** v4.5.0 (Phase 12 complete — all automated tasks done; 12.35 demo video + 12.36 YouTube = human tasks)
**Stack:** Python 3.11+ · FastAPI 0.115 (async, port 8000) · Celery 5.4 · PostgreSQL 15 · Redis 5.2 · Semgrep · Bandit · Ruff · Vulture · gosec · staticcheck · ESLint · npm audit · Trivy · TruffleHog · JWT + API keys
**Repo:** `ahmed-145/ACR-QA` · **Branch:** always push to `main`

---

## Before Every Commit — Non-Negotiable

Run these three commands in order. All must pass before committing:

```bash
# 1. Format + lint
.venv/bin/ruff format CORE/ DATABASE/ FRONTEND/ TESTS/
.venv/bin/ruff check --fix CORE/ DATABASE/ FRONTEND/ TESTS/

# 2. Type check
.venv/bin/mypy CORE/ --ignore-missing-imports --no-error-summary | grep "error:"
# Expected: 0 lines of output (0 errors)

# 3. Tests (default — fast PR suite, slow markers excluded)
.venv/bin/pytest TESTS/ -q --tb=short
# Expected: 2274 passed, 31 skipped, 15 deselected, 0 failed
# Coverage ≥ 82% (CI gate)

# 3b. Slow suite (only run before pushing thesis-relevant changes; otherwise nightly CI handles it)
.venv/bin/pytest TESTS/ -m slow -q --no-cov
# Expected: 6 passed, ~2289 deselected
# Runs the recall battery against DVPWA/Pygoat/DSVW/VulPy + the no-CUSTOM-* guard.
# Skips cleanly if test_targets/ is missing (gitignored).

# 3c. Everything (rare — confidence check before a release)
.venv/bin/pytest TESTS/ -m "slow or not slow" -q --no-cov
```

> These are also enforced by `.pre-commit-config.yaml` — the commit will be **blocked** if any fail.

---

## Code Standards

- **Formatter:** Ruff (replaces black + isort + flake8 — do NOT install these separately)
- **Type checker:** mypy 1.20+ with `--ignore-missing-imports`
- **Python version:** 3.11+ — use `X | Y` union syntax, `match`, etc. freely
- **No bare `except:`** — always catch specific exceptions
- **No `print()` in production code** — use `logger = logging.getLogger(__name__)`
- **No hardcoded secrets** — use `.env` file (already gitignored)
- **All new functions must have docstrings** (even one-liners)

---

## Architecture (What Lives Where)

```
CORE/engines/         ← Analysis pipeline (normalizer, scorer, explainer, autofix, quality_gate, triage_memory, etc.)
CORE/config_loader.py ← Reads .acrqa.yml per-repo policy
CORE/main.py          ← Pipeline orchestrator (writes findings.json + findings_pid<NNN>.json)
CORE/tasks.py         ← Celery tasks for async scan dispatch (run_analysis_task)
DATABASE/database.py  ← PostgreSQL: 8 tables (runs, findings, explanations, feedback, metrics, suppression_rules, users, api_keys)
FRONTEND/app.py       ← Legacy Flask dashboard (port 5000) — being migrated onto FastAPI
FRONTEND/api/         ← FastAPI app (port 8000): main.py, models.py, deps.py + routers/{auth,runs,scans}.py
FRONTEND/auth/        ← jwt_utils.py, api_key_utils.py
alembic/              ← DB migrations (baseline + users/api_keys)
TESTS/                ← pytest (1,699 default + 6 slow; ~85% coverage)
TESTS/evaluation/     ← Layer 5 — ground-truth YAMLs + recall harness (slow-marked, nightly CI)
TESTS/test_no_custom_rules.py ← Regression guard: zero CUSTOM-* findings on DSVW (slow)
TESTS/test_celery_tasks.py    ← CORE/tasks.py coverage (eager mode, no Redis required)
scripts/              ← CLI utilities (run_evaluation, test_gap_analyzer, feedback_tuner, validate_config, seed_admin, etc.)
TOOLS/semgrep/        ← Custom Semgrep rules (python-rules.yml + js-rules.yml)
config/rules.yml      ← Knowledge base: every canonical rule → description + remediation
```

---

## Critical Rules

1. **CUSTOM-* findings = bug** — never acceptable in output. Add missing rule to `RULE_MAPPING` in `normalizer.py` AND `RULE_SEVERITY` in `severity_scorer.py`. (Phase 1 just closed UP012/UP028/UP045; pattern keeps recurring.)
2. **Changing RULE_SEVERITY?** → also update test assertions in `test_deep_coverage.py::TestSeverityScorer`
3. **Finding field names:** use `file` and `line` — NOT `file_path` / `line_number`
4. **Run scans sequentially.** Parallel ACR-QA scans on the same workspace currently collide via shared `DATA/outputs/<tool>.json` intermediate files. Per-process workspaces are a planned Phase 2 fix.
5. **Coverage % is a tripwire, not a target.** Don't pump coverage by writing trivial unit tests — Layer 5 evaluation benchmarks (real repos, ground truth) is what proves the tool works. Ground truth lives in YAML at `TESTS/evaluation/ground_truth/`; documented gaps use `out_of_scope: <reason>` rather than fudging recall numbers. See `GOD_MODE_PLAN.md` §9.
6. **Every session must end with a commit + push** (Ahmed's preference)
7. **Update docs alongside code** — see Doc Map in `AGENT_NOTES.md`
8. **Version must stay in sync:** `CORE/__init__.py` and `CORE/main.py` — always same version string

---

## Documentation Files (Keep Updated)

| Doc | Update When |
|-----|------------|
| `docs/TESTING_AND_CALIBRATION.md` | Any bug found or fixed |
| `docs/CHANGELOG.md` | Every version change |
| `README.md` | Badge numbers (tests, version) |
| `docs/evaluation/EVALUATION.md` | Metrics, precision, coverage |
| `docs/README.md` | Any new doc created |

---

## Environment

- **Venv:** `.venv/` — always use `.venv/bin/python`, `.venv/bin/pytest`, etc.
- **`.env` file:** exists at project root, gitignored. Contains `GROQ_API_KEY_1..4`, `GITHUB_TOKEN`, `DATABASE_URL`, `JWT_SECRET_KEY`, `ADMIN_EMAIL/PASSWORD`.
- **Docker:** `docker compose up -d` → starts Postgres + Redis + Flask app + FastAPI + Celery worker + Prometheus + Grafana
- **Dashboard (legacy Flask):** `python3 FRONTEND/app.py` → http://localhost:5000
- **API (FastAPI):** `make api` → http://localhost:8000 (Swagger at `/docs`)
- **Background worker:** `make worker` (Celery)

---

## What This Project Is NOT

- Not a SaaS tool — it's a **thesis deliverable**. Correctness > features.
- Not a replacement for human review — it's a **decision-support tool**.
- Does not detect: CSRF, IDOR, auth bypass, business logic bugs (static analysis limits — intentional).
