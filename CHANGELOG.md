# Changelog

All notable changes to ACR-QA are documented here.

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
- RAG-enhanced AI explanations (Cerebras)
- PostgreSQL provenance database
- Flask dashboard
- Basic analysis pipeline
