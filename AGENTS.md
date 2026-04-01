# AGENTS.md
# Universal AI agent instructions for ACR-QA.
# Any AI tool (Claude Code, Copilot, Cursor, Windsurf, etc.) should read this before touching code.
# For deeper project memory and gotchas, read AGENT_NOTES.md (gitignored, local only).

---

## Project

**ACR-QA** — Automated Code Review & Quality Assurance
Graduation thesis project for Ahmed at KSIU. Supervisor: Dr. Samy.
**Stack:** Python 3.11+, Flask, PostgreSQL, Redis, Semgrep, Bandit, Ruff, Vulture
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

# 3. Tests
.venv/bin/pytest TESTS/ -q --tb=short
# Expected: 370+ passed, 0 failed
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
CORE/engines/         ← Analysis pipeline (normalizer, scorer, explainer, autofix, quality_gate)
CORE/config_loader.py ← Reads .acrqa.yml per-repo policy
CORE/main.py          ← Pipeline orchestrator
DATABASE/database.py  ← PostgreSQL: 5 tables (runs, findings, explanations, feedback, metrics)
FRONTEND/app.py       ← Flask dashboard + 20+ REST API endpoints
TESTS/                ← pytest (374 tests across 5 files)
scripts/              ← CLI utilities (test_gap_analyzer, feedback_tuner, validate_config, etc.)
TOOLS/semgrep/        ← Custom Semgrep rules
config/rules.yml      ← Knowledge base: every canonical rule → description + remediation
```

---

## Critical Rules

1. **CUSTOM-* findings = bug** — never acceptable in output. Add missing rule to `RULE_MAPPING` in `normalizer.py` AND `RULE_SEVERITY` in `severity_scorer.py`.
2. **Changing RULE_SEVERITY?** → also update test assertions in `test_deep_coverage.py::TestSeverityScorer`
3. **Finding field names:** use `file` and `line` — NOT `file_path` / `line_number`
4. **Every session must end with a commit + push** (Ahmed's preference)
5. **Update docs alongside code** — see Doc Map in `AGENT_NOTES.md`
6. **Version must stay in sync:** `CORE/__init__.py` and `CORE/main.py` — always same version string

---

## Documentation Files (Keep Updated)

| Doc | Update When |
|-----|------------|
| `docs/TESTING_AND_CALIBRATION.md` | Any bug found or fixed |
| `CHANGELOG.md` | Every version change |
| `README.md` | Badge numbers (tests, version) |
| `docs/evaluation/EVALUATION.md` | Metrics, precision, coverage |
| `docs/README.md` | Any new doc created |

---

## Environment

- **Venv:** `.venv/` — always use `.venv/bin/python`, `.venv/bin/pytest`, etc.
- **`.env` file:** exists at project root, gitignored. Contains `CEREBRAS_API_KEY`, `GITHUB_TOKEN`, `DATABASE_URL`.
- **Docker:** `docker compose up -d` → starts Postgres + Redis + App + Prometheus + Grafana
- **Dashboard:** `python3 FRONTEND/app.py` → http://localhost:5000

---

## What This Project Is NOT

- Not a SaaS tool — it's a **thesis deliverable**. Correctness > features.
- Not a replacement for human review — it's a **decision-support tool**.
- Does not detect: CSRF, IDOR, auth bypass, business logic bugs (static analysis limits — intentional).
