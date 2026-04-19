# Changelog

All notable changes to ACR-QA are documented here.

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
- RAG-enhanced AI explanations (Cerebras)
- PostgreSQL provenance database
- Flask dashboard
- Basic analysis pipeline
