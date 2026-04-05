# Changelog

All notable changes to ACR-QA are documented here.

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
- RAG-enhanced AI explanations (Cerebras)
- PostgreSQL provenance database
- Flask dashboard
- Basic analysis pipeline
