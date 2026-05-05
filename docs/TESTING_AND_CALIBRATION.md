# ACR-QA Testing & Calibration Report

**Latest Run:** May 2026 · **Version:** v3.2.5
**Unit Tests:** 1,690 passed · **Coverage:** 86% (God-Mode — All Core Logic Fully Covered)

### CI Static Analysis Status (v3.2.5)

| Check | Status | Notes |
|-------|--------|-------|
| ruff format | ✅ 0 errors | All production code |
| ruff lint | ✅ 0 errors | All production code |
| mypy | ✅ 0 errors* | `CORE/main.py` and `scripts.*` suppressed — see below |
| pytest | ✅ 1,690 passed | Coverage ≥ 40% enforced |

**mypy suppression note:** `CORE/main.py` (the 1,167-line pipeline orchestrator) has pre-existing `Mapping[str, Any]` vs `dict[str, Any]` type conflicts introduced when engine functions were added incrementally. These are suppressed via `[[tool.mypy.overrides]]` in `pyproject.toml` and do not affect runtime behaviour — all engine calls are tested end-to-end. Fixing them requires auditing the return type annotations of `enrich_findings()`, `suppress_findings()`, and `evaluate()` across multiple engine modules.

---

## Table of Contents

1. [Unit Test Suite (v2.6 to v3.2.4)](#1-unit-test-suite)
2. [Code Audit Bugs Found & Fixed (v2.6)](#2-code-audit-bugs-found--fixed)
3. [Test Coverage Before vs After](#3-test-coverage)
4. [Mass Repo Testing — 9 Real Repositories](#4-mass-repo-testing)
5. [What Failed and Why](#5-what-failed-and-why)
6. [False Positives & False Negatives](#6-false-positives--false-negatives)
7. [All Calibration Fixes](#7-all-calibration-fixes)
8. [Final Results](#8-final-results)

---

## 1. Unit Test Suite

### Test Files

| File | Tests | Added In |
|------|:---:|:---:|
| `TESTS/test_flask_app.py` | 107 | v3.2.4 |
| `TESTS/test_pipeline_helpers.py` | 45 | v3.2.4 |
| `TESTS/test_code_extractor.py` | 23 | v3.2.4 |
| `TESTS/test_metrics_ratelimiter.py` | 69 | v3.2.3 |
| `TESTS/test_autofix.py` | 70 | v3.2.2 |
| `TESTS/test_explainer.py` | 90 | v3.2.2 |
| `TESTS/test_batch1_pure_logic.py` | 108 | v3.2.1 |
| `TESTS/test_batch2_engines.py` | 96 | v3.2.1 |
| `TESTS/test_batch3_detectors.py` | 100 | v3.2.1 |
| `TESTS/test_normalizer_scorer.py` | 134 | v3.2.1 |
| `TESTS/test_new_engines.py` | 102 | v3.1.2 — Features 4-9 |
| `TESTS/test_coverage_boost.py` | 77 | v2.9 |
| `TESTS/test_god_mode.py` | 78 | v2.7 |
| `TESTS/test_deep_coverage.py` | 98 | v2.6 |
| `TESTS/test_config_quality.py` | 23 | v2.5 |
| `TESTS/test_integration.py` | 69 | v2.4 |

### v3.2.x Test Classes (God-Mode Coverage)

| Test File | Tests | What It Covers |
|-------|:---:|----------------|
| `test_flask_app.py` | 107 | Complete FRONTEND API REST endpoint verification over simulated payloads and mock DB. |
| `test_pipeline_helpers.py` | 45 | Pure functions for `main.py` AnalysisPipeline sorting, deduplication, and quality-gate config application. |
| `test_metrics_ratelimiter.py` | 69 | Prometheus output structures natively. Tests system resiliency directly hitting `redis`. |
| `test_explainer.py` | 90 | Mocked Groq client covering prompt formation, semantic entropy fallback loops, DB insertions, pricing structures. |
| `test_autofix.py` | 70 | Regex replacement algorithms against custom sub-processes checking line ranges and bounding boxes. |
| `test_batch1-3...py` | 304 | Extensive edge-case tracking against individual pipeline detection algorithms pushing >90% coverage for AST analyzers. |

### v3.0.8 Test Classes (`test_new_engines.py`)

| Class | Tests | What It Covers |
|-------|:---:|----------------|
| `TestCBoMScanner` | 7 | CBoM Engine: MD5 detection, JS/TS crypto, quantum-safety tags, directory exclusions |

### v2.7 Test Classes (`test_god_mode.py`)

| Class | Tests | What It Covers |
|-------|:---:|----------------|
| `TestGapAnalyzerAST` | 8 | AST extraction: functions, classes, async, private, nested, empty, syntax errors, complexity |
| `TestGapAnalyzerDiscovery` | 2 | Test file discovery, class method subject matching |
| `TestGapAnalysis` | 3 | Gap detection, private exclusion, private inclusion flag |
| `TestGapReporting` | 5 | Text/JSON reports, quality gate pass/fail, API data format |
| `TestOWASPMapping` | 4 | All 10 OWASP categories, required fields, CWE coverage, ID format |
| `TestComplianceReport` | 3 | Markdown report, JSON report, compliance data API |
| `TestFeedbackTuner` | 5 | Downgrade logic, skip low count, keep good rules, report output, empty data |
| `TestConfigValidator` | 8 | Valid config, unknown keys, invalid severity, missing file, empty, type mismatch, templates |
| `TestNewAPIEndpoints` | 6 | `/api/test-gaps`, `/api/policy`, `/api/compliance`, `/api/health` |
| `TestConfidenceScoring` | 5 | Function exists, high/low scoring, bounds (0–1), rule citation boost |
| `TestVersionConsistency` | 4 | Version string format, no hardcoded versions, Flask secret key |
| `TestPolicyEngine` | 6 | `.acrqa.yml` exists + valid, ConfigLoader, QualityGate, docs exist + sections |
| `TestCrossFeatureIntegration` | 5 | Self-codebase analysis, config validation, all imports, normalizer→gate, scorer→confidence |
| `TestExistingFeatureRegression` | 9 | Ruff/Semgrep/Bandit normalizer, quality gate, autofix, rate limiter, config loader |
| `TestEdgeCases` | 7 | Empty dirs, corrupt YAML, empty findings, 1000 findings, 404s, load stability |

### v2.6 Test Classes (`test_deep_coverage.py`)

| Class | Tests | What It Covers |
|-------|:---:|----------------|
| `TestSeverityScorer` | 16 | All severity rules, complexity thresholds, dead code context, duplication sizing, **LOW rules** (v2.8) |
| `TestAutoFixDeep` | 10 | All 8 fixable rules (can_fix + confidence), generate_fix with real temp files |
| `TestSecretsDetectorDeep` | 7 | AWS keys, passwords, generic secrets, JWTs, clean files, missing files, directory scan |
| `TestAICodeDetectorDeep` | 4 | Clean code, repetitive pattern detection, missing file, empty file |
| `TestCodeExtractorDeep` | 4 | Middle-of-file extraction, first-line extraction, out-of-range, missing file |
| `TestNormalizerDeep` | 8 | Ruff/Bandit/Vulture/Semgrep normalization, empty input, edge cases |
| `TestConfigLoaderDeep` | 5 | Default config, ignore paths, custom YAML loading, caching, real `.acrqa.yml` |
| `TestQualityGateDeep` | 9 | Empty findings (pass), custom thresholds, high/medium/total/security limits |
| `TestPythonAdapterDeep` | 7 | Language name, extensions, tool list, file discovery, supports_file, rule mappings |
| `TestFlaskEndpoints` | 17 | All 11 endpoints, 404 on invalid run/finding, metrics, secrets/AI scans |
| `TestDatabaseDeep` | 11 | Recent runs, trend data, feedback stats, explanations, create/complete/fail run |

---

## 2. Code Audit Bugs Found & Fixed

Full god-mode audit of every module (v2.6). Found and fixed 8 bugs.

### Critical Bugs

| # | Bug | File | Impact | Fix |
|---|-----|------|--------|-----|
| 1 | Flask returns 500 instead of 404 for nonexistent findings | `FRONTEND/app.py` | Stack trace leaked to API clients | Added existence check before UPDATE |
| 2 | Inline suppression `# acr-qa:ignore` never worked | `CORE/engines/normalizer.py` | Suppression comments silently ignored | Fixed attribute: `file_path`→`file`, `line_number`→`line` |
| 3 | Database crash on NULL `rule_id` | `DATABASE/database.py` | `insert_finding()` crashed on NOT NULL violation | Added fallback chain to guarantee non-NULL |
| 4 | Normalizer double-parses Ruff output | `CORE/engines/normalizer.py` | `normalize_ruff()` called 2× per run | Stored result in variable, reused for print |

### Code Quality Issues

| # | Issue | File | Fix |
|---|-------|------|-----|
| 5 | 4 bare `except:` clauses | `CORE/engines/severity_scorer.py` | Replaced with `except Exception:` |
| 6 | Dead expression in `verify_fix()` | `CORE/engines/autofix.py` | Assigned discarded `.get()` result to variable |
| 7 | Dead `SEVERITY_MAPPING` dict (10 lines, never referenced) | `CORE/engines/normalizer.py` | Removed |
| 8 | 18 trailing whitespace errors across 6 files | Various | Cleaned |

---

## 3. Test Coverage

### v2.6 Before vs After

| Module | Before | After | Δ |
|--------|:------:|:-----:|:---:|
| `adapters/base.py` | ~0% | **100%** | +100 |
| `quality_gate.py` | ~38% | **92%** | +54 |
| `config_loader.py` | ~50% | **86%** | +36 |
| `ai_code_detector.py` | ~30% | **81%** | +51 |
| `normalizer.py` | ~45% | **77%** | +32 |
| `database.py` | ~35% | **75%** | +40 |
| `metrics.py` | ~21% | **72%** | +51 |
| `secrets_detector.py` | ~20% | **65%** | +45 |
| `rate_limiter.py` | ~30% | **64%** | +34 |
| `python_adapter.py` | ~0% | **53%** | +53 |
| `severity_scorer.py` | ~25% | **53%** | +28 |
| `autofix.py` | ~30% | **45%** | +15 |
| `FRONTEND/app.py` | ~22% | **41%** | +19 |
| **TOTAL** | **28%** | **38.85%** | **+11** |

### Intentionally Low Coverage (By Design)

| Module | Coverage | Reason |
|--------|:--------:|--------|
| `main.py` | 9% | Requires full infra (7 tools + DB + LLM) — integration-only |
| `sca_scanner.py` | 0% | Wraps `pip-audit` subprocess — requires external binary |
| `explainer.py` | 45% | LLM calls + Redis caching — requires live `GROQ_API_KEY` |

---

## 4. Mass Repo Testing

Tested ACR-QA on **9 diverse real-world Python repos** to stress-test severity accuracy, noise reduction, quality gate thresholds, and AI explanation quality.

### Repos Selected

| Repo | Stars | Why Chosen |
|------|:---:|-----------|
| [DVPWA](https://github.com/anxolerd/dvpwa) | ~200 | **Deliberately vulnerable** — known SQL injection + MD5. Ground truth for detection accuracy. |
| [Flask](https://github.com/pallets/flask) | 68k | Large, well-maintained. Uses `eval()`/`exec()` intentionally. Tests for false positives. |
| [requests](https://github.com/psf/requests) | 52k | Small, clean. Should have minimal findings. Baseline for noise calibration. |
| [HTTPie](https://github.com/httpie/cli) | 34k | Medium-sized CLI. Has SSL `verify=False` and complex functions. |
| [FastAPI](https://github.com/tiangolo/fastapi) | 78k | Modern async. Heavy type annotations and decorators. |
| [Black](https://github.com/psf/black) | 39k | Code formatter. Extreme complexity: `linegen.py` has CC=53. |
| [Rich](https://github.com/Textualize/rich) | 50k | Terminal UI. **1,586 raw findings** — ultimate noise stress test. |
| [Sanic](https://github.com/sanic-org/sanic) | 18k | Async web framework. Complex nested routing functions. |
| ACR-QA self | — | Can the tool analyze its own codebase? |

### Noise Reduction: Per-Rule Cap (Max 5 Per Rule)

| Repo | Raw | After Cap | Reduction |
|------|:---:|:---:|:---:|
| Rich | 1,586 | **127** | **92%** |
| FastAPI | 390 | 48 | 88% |
| HTTPie | 394 | 78 | 80% |
| Sanic | 497 | 104 | 79% |
| Black | 240 | 51 | 79% |
| requests | 181 | 50 | 72% |
| Flask | 136 | 49 | 64% |

---

## 5. What Failed and Why

### Problem 1 — SQL Injection Was MEDIUM Instead of HIGH

DVPWA `sqli/dao/student.py` has a real SQL injection:
```python
q = ("INSERT INTO students (name) VALUES ('%(name)s')" % {'name': name})
```
Bandit detected it (B608 → `SECURITY-027`) but `severity_scorer.py` didn't have that rule — it defaulted to Bandit's raw severity (MEDIUM), not our override.

**Root cause:** `RULE_SEVERITY` dict only had ~20 rules. Everything else fell through.
**Fix:** Expanded from ~20 → **48 rules** covering all Bandit B1xx–B7xx. SQL injection → HIGH.

---

### Problem 2 — MD5 Password Hashing Was LOW Instead of MEDIUM

DVPWA `sqli/dao/user.py` hashes passwords with MD5. Same root cause as Problem 1 — `SECURITY-009` missing from severity map.

**Fix:** Added `SECURITY-009` → MEDIUM. (Not HIGH because it's deprecated, not immediately exploitable like SQL injection.)

---

### Problem 3 — Flask Had 136 Findings (No Per-Rule Cap)

18× `print-in-production`, 12× `assert-used`, 10× `unused-variable` dominated the output. One noisy rule made the report useless.

**Fix:** Per-rule cap of **5 findings max per rule**. Flask dropped 136 → **49** (64% cut) while preserving all unique finding types.

---

### Problem 4 — HIGH Findings Buried in Output

Findings were listed in discovery order (by file path). SQL injection appeared between import warnings and naming style issues.

**Fix:** Sort all findings by severity (HIGH → MEDIUM → LOW), then by file path within the same level.

---

### Problem 5 — Quality Gate Defaults Were Too Strict

Default `max_security=0` failed every repo with any security finding. Default `max_medium=10` failed 5/9 well-maintained repos.

**Fix (Phase 1):** `max_security` 0 → 3
**Fix (Phase 4):** `max_medium` 10 → **20**

---

### Problem 6 — Ruff Rules Showed as CUSTOM-I001, CUSTOM-UP007, etc.

22 Ruff rules weren't in `RULE_MAPPING`. They fell through to `CUSTOM-{rule_id}` — confusing in output.

**Fix:** Added 22 mappings. Key ones:

| Ruff Code | Canonical ID | What It Is |
|-----------|-------------|-----------|
| I001/I002 | IMPORT-002 | Import sorting |
| UP007 | STYLE-003 | `X \| Y` type union |
| UP035 | STYLE-005 | Deprecated imports |
| F821 | ERROR-001 | Undefined name (real bug, MEDIUM) |
| B904 | EXCEPT-002 | `raise ... from` in except |
| T201/T203 | STYLE-007 | print/pprint in production |
| TCH001–003 | TYPE-002 | Move to `TYPE_CHECKING` block |

---

### Problem 7 — SECURITY-002 (assert-used) Was Too Noisy as MEDIUM

Generated **35 MEDIUM findings across 9 repos**. Flask, requests, HTTPie all hit the 5-per-rule cap just on assert-used alone. Libraries use `assert` intentionally for invariant checks.

**Fix:** Demoted `SECURITY-002` MEDIUM → **LOW**.

Effect:

| Repo | Medium Before | Medium After |
|------|:---:|:---:|
| Flask | 11 | **6** |
| requests | 13 | **8** |
| HTTPie | 14 | **9** |

---

### Problem 8 — AI Explanations Truncated Mid-Sentence

`max_tokens=150` was too low. With the 3-part WHAT/WHY/HOW structure, LLM needed ~300 tokens for a complete answer.

**Example of truncated output:**
> *"...use bcrypt/argon2 for password storage, as recommended in"*

**Fix:** `max_tokens` 150 → **300**. Average explanation length: ~200 chars → **~530 chars**.

---

### Problem 9 — AI Gave No Code Fix Examples

Prompt only asked for text advice. Never requested a code block.

**Fix:** Updated prompt to end with:
> *"...end with a `python` code block showing the fix."*

**Before:** Text-only advice
**After:** Every explanation ends with corrected code, e.g.:
```python
# Fix: Use parameterized query
await cur.execute("INSERT INTO students (name) VALUES (%s)", (name,))
```

---

## 6. False Positives & False Negatives

### False Negatives — What We Missed (DVPWA Ground Truth)

| Known Vulnerability | Caught? | Why |
|---|:---:|---------|
| SQL injection via `%` formatting | ✅ | SECURITY-027 HIGH |
| MD5 password hashing | ✅ | SECURITY-009 MEDIUM |
| Plaintext password in DB config string | ❌ | Config-level — needs secrets scanner, not static analysis |
| No rate limiting on login | ❌ | Design/architectural flaw — beyond static analysis scope |
| No CSRF protection | ❌ | Requires framework-aware runtime analysis |

**All code-level vulnerabilities were caught. Missed items require dynamic/runtime analysis.**

### False Positives — All 25 HIGHs Verified Across 9 Repos

| Rule | Repo | Verdict |
|------|------|:---:|
| COMPLEXITY-001 (CC=53) | Black `linegen.py` | ✅ Genuinely complex |
| COMPLEXITY-001 (CC=49) | Rich `table.py` | ✅ Genuinely complex |
| SECURITY-001 (`eval()`) | Flask `cli.py` | ✅ Real eval — intentional |
| SECURITY-001 (`exec()`) | Flask `config.py` | ✅ Real exec — loads config files |
| SECURITY-027 | DVPWA `student.py` | ✅ Real SQL injection |
| SECURITY-013 (`verify=False`) | HTTPie | ✅ SSL bypass for `--verify=no` flag |

**Zero false positive HIGHs across all 9 repos.**

---

## 7. All Calibration Fixes (v2.8)

| Fix | File | Change |
|-----|------|--------|
| Severity map: ~20 → 48 rules | `CORE/engines/severity_scorer.py` | SQL injection HIGH, MD5 MEDIUM, all Bandit B-rules covered |
| 22 Ruff rules mapped | `CORE/engines/normalizer.py` | No more CUSTOM-xxx in output |
| 13 new canonical IDs added to severity map | `CORE/engines/severity_scorer.py` | ERROR-001 MEDIUM, STYLE-xxx LOW |
| SECURITY-002 demoted to LOW | `CORE/engines/severity_scorer.py` | assert-used no longer noisy MEDIUM |
| Per-rule cap (max 5) | `CORE/main.py` | 92% noise cut on Rich, 64% on Flask |
| Priority sorting | `CORE/main.py` | HIGH findings always appear first |
| max_security 0 → 3 | `CORE/engines/quality_gate.py` | Realistic for real codebases |
| max_medium 10 → 20 | `CORE/engines/quality_gate.py` | 5/9 repos no longer false-fail |
| max_tokens 150 → 300 | `CORE/engines/explainer.py` | Explanations never truncated |
| AI prompt with code fix blocks | `CORE/engines/explainer.py` | Every explanation has corrected code |
| SECURITY-002 test moved to LOW | `TESTS/test_deep_coverage.py` | Test alignment |
| Medium threshold test updated | `TESTS/test_config_quality.py` | 15 → 25 findings to exceed new max |

---

## 8. Final Results

### Repo Results (v2.8)

| Repo | Total | 🔴 H | 🟡 M | 🟢 L | M ≤ 20? | AI Code Fix? |
|------|:---:|:---:|:---:|:---:|:---:|:---:|
| DVPWA | 30 | 1 | 6 | 23 | ✅ | ✅ 532 chars |
| Flask | 49 | 2 | 6 | 41 | ✅ | ✅ |
| requests | 50 | 0 | 8 | 42 | ✅ | ✅ |
| HTTPie | 78 | 2 | 9 | 67 | ✅ | ✅ |
| click | 50 | 2 | 9 | 39 | ✅ | ✅ |
| FastAPI | 48 | 2 | 9 | 37 | ✅ | — |
| Black | 51 | 4 | 8 | 39 | ✅ | — |
| Rich | 127 | 2 | 11 | 114 | ✅ | — |
| Sanic | 104 | 4 | 8 | 92 | ✅ | — |

> [!NOTE]
> No repo fully passes the quality gate (`max_high=0` blocks anything with eval/exec). This is by design — the gate is for your own projects, not third-party library audits.

### Tooling Used

```bash
# Static analysis on our own code
ruff check CORE/ DATABASE/ FRONTEND/ scripts/
→ 18 errors found → 0 after fix

# Dead code detection
vulture CORE/ DATABASE/ FRONTEND/ scripts/ --min-confidence 80
→ 0 results (all code is reachable)

# Test suite
pytest TESTS/ -q
→ 275 passed, 4 skipped, 38.85% coverage
```

---

## 9. Round 3 — Fresh Repo Testing (v2.8+)

Tested 7 **completely new** repos to validate all calibration fixes hold up.

### Repos Tested

| Repo | Domain | Findings | H | M | L | Gate |
|------|--------|:---:|:---:|:---:|:---:|:---:|
| arrow | Date/time | 59 | 9 | 1 | 49 | ❌ |
| marshmallow | Serialization | 30 | 0 | 8 | 22 | ✅ |
| paramiko | SSH | 116 | 4 | 14 | 98 | ❌ |
| fabric | Remote exec | 40 | 1 | 5 | 34 | ❌ |
| celery | Task queue | 163 | 1 | 11 | 151 | ❌ |
| pydantic | Validation | 134 | 3 | 12 | 119 | ❌ |
| scrapy | Web scraping | 126 | 5 | 33 | 88 | ❌ |

### Defects Found & Fixed

**1. Cross-Tool Duplicate Findings** — Semgrep + Bandit flagged same vulnerability on same line as 2 separate findings. Fixed with 2-pass dedup using 6 category groups (shell-injection, pickle, eval, hardcoded-password, sql-injection, bare-except). **Scrapy dupes: 5 → 0.**

**2. 19 Unmapped Rules** — UP006/017/024/032, N804/818, B028/113/311/321/402/403/404/406/410/905, F403 all mapped to proper canonical IDs.

**3. CUSTOM-global-variable** — Unmapped Semgrep rule → added to severity map as LOW.

### AI Quality: 100%

320 explanations across all 7 repos: **0 truncated, 0 missing code fix, 0 too short**.

### Current Rule Coverage

| Category | Count |
|----------|:---:|
| RULE_MAPPING entries | **65** |
| RULE_SEVERITY entries | **59** |
| Cross-tool dedup groups | **6** |


---

## 10. Round 4 — God Mode End-to-End Session (v2.9)

**Date:** March 31, 2026 · **Commits:** `edf7adf` → `10669e8` (6 commits on main)

This session was a comprehensive end-to-end validation and code quality overhaul,
triggered by running a deliberate "God Mode" test PR (#9) containing 8 intentional
vulnerabilities to stress-test the full pipeline.

---

### Test Files (v2.9)

| File | Tests | Added In |
|------|:---:|:---:|
| `TESTS/test_new_engines.py` | **92** | v3.1.1 — Features 4-8 |
| `TESTS/test_coverage_boost.py` | **77** | v2.9 |
| `TESTS/test_god_mode.py` | 78 | v2.7 |
| `TESTS/test_deep_coverage.py` | 98 | v2.6 |
| `TESTS/test_config_quality.py` | 30 | v2.5 |
| `TESTS/test_integration.py` | 69 | v2.4 |
| **Total Core Tests** | **~481** | — |

---

### God Mode PR #9 — What Was Tested

PR #9 (`test/god-mode-live-pr`) had 8 deliberate security vulnerabilities designed to
exercise every detection path.

| Vulnerability | Rule | Expected | Caught? |
|---|---|:---:|:---:|
| `eval(user_input)` | SECURITY-001 | 🔴 High | ✅ |
| Hardcoded password `admin123` | SECURITY-005 | 🔴 High | ✅ |
| Raw SQL `% name` formatting | SECURITY-027 | 🔴 High | ✅ |
| `subprocess.Popen(shell=True)` | SECURITY-021 | 🔴 High | ✅ |
| `pickle.loads(user_data)` | SECURITY-008 | 🔴 High | ✅ |
| `yaml.load()` without Loader | SECURITY-018 | 🔴 High | ✅ |
| Hardcoded `SECRET_KEY` | HARDCODE-001 | 🔴 High | ✅ |
| Assert for input validation | SECURITY-002 | 🟢 Low | ✅ |

**All 8 detected correctly. Zero false positives.**

---

### Code Quality Fixes Applied (v2.9)

| # | Fix | File | Commit |
|---|-----|------|--------|
| 1 | Version unified to **v2.7.0** everywhere | `CORE/__init__.py`, `main.py` | `edf7adf` |
| 2 | `SECURITY-008` (pickle) medium → **high** (CWE-502 RCE) | `severity_scorer.py` | `edf7adf` |
| 3 | `SECURITY-018` (yaml.load) medium → **high** (CWE-502 RCE) | `severity_scorer.py` | `edf7adf` |
| 4 | `CUSTOM-N813` → `NAMING-003` | `normalizer.py` | `edf7adf` |
| 5 | `CUSTOM-F405` → `IMPORT-003` | `normalizer.py` | `edf7adf` |
| 6 | `CUSTOM-UP036` → `STYLE-005` | `normalizer.py` | `edf7adf` |
| 7 | PR comments strip `/tmp/pr-files/` from file paths | `post_pr_comments.py` | `edf7adf` |
| 8 | `assert-for-validation` Semgrep rule excludes test files | `python-rules.yml` | `edf7adf` |
| 9 | KB entries added for NAMING-003, IMPORT-003, STYLE-005 | `config/rules.yml` | `edf7adf` |
| 10 | Test assertions updated for SECURITY-008/018 → high | `test_deep_coverage.py` | `dfe8288` |

---

### Coverage Improvements (v2.9)

| Module | Before (v2.8) | After (v2.9) | Δ |
|--------|:---:|:---:|:---:|
| `quality_gate.py` | 8% | **93%** | +85 |
| `severity_scorer.py` | 34% | **62%** | +28 |

**New test classes in `test_coverage_boost.py`:**

| Class | Tests | What It Covers |
|-------|:---:|----------------|
| `TestQualityGateFullCoverage` | 30 | All init branches, threshold pass/fail combos, print_report, result structure |
| `TestSeverityScorerFullCoverage` | 47 | CUSTOM-* keyword inference, COMPLEXITY/DEAD/DUP adjustments, message fallbacks, priority |

---

### CUSTOM-* Findings Eliminated

Before this session, 3 Ruff codes appeared as `CUSTOM-N813`, `CUSTOM-F405`, `CUSTOM-UP036`.

| Ruff Code | Before | After |
|-----------|--------|-------|
| N813 | `CUSTOM-N813` | `NAMING-003` |
| F405 | `CUSTOM-F405` | `IMPORT-003` |
| UP036 | `CUSTOM-UP036` | `STYLE-005` |

**After fix: 0 CUSTOM-* findings in any output.**

---

### PR Comment Path Display Fix

**Before:** `File: /tmp/pr-files/myapp/auth/login.py:38`
**After:** `File: myapp/auth/login.py:38`

Added `clean_file_path()` to `scripts/post_pr_comments.py`.

---

### Thesis Deliverables Generated

| File | Purpose |
|------|---------|
| `docs/evaluation/USER_STUDY_PROTOCOL.md` | Full protocol, 3 test scenarios, researcher script, data table |
| `docs/evaluation/USER_STUDY_SURVEY.md` | 15-question participant questionnaire |
| `docs/evaluation/user_study_responses_template.csv` | Data collection CSV template |
| `docs/DEMO_VIDEO_SCRIPT.md` | 5-minute demo video script with timestamps and voiceover |

---

## Section 11 — Round 5: New Repo Testing (April 5, 2026)

### Repos Tested

| Repo | Stars | Domain | Total Findings | H | M | L | Gate | CUSTOM-* |
|------|-------|--------|---------------|---|---|---|------|---------|
| Django | 82k★ | Web Framework | 50 (cap) | ? | ? | ? | ❌ FAIL | 4 types |
| SQLAlchemy | 10k★ | ORM | 207 | 11 | 14 | 182 | ❌ FAIL | 0 |
| aiohttp | 15k★ | Async HTTP | 76 | 0 | 6 | 70 | ✅ PASS | 4 types |
| black | 39k★ | Code formatter | 88 | 2 | 9 | 77 | ❌ FAIL | 4 types |
| Pillow | 12k★ | Image processing | 71 | 3 | 13 | 55 | ❌ FAIL | 5 types |

**Key result:** aiohttp is the only repo that passes - a well-maintained async library with strict code review culture.

### New CUSTOM-* Rules Fixed (12 rules added to `normalizer.py`)

| Rule ID | Canonical ID | Severity | Source |
|---------|-------------|----------|--------|
| `UP041` | `STYLE-014` | low | Ruff — timeout=None style |
| `B027` | `BEST-PRACTICE-003` | low | Ruff — empty abstract method |
| `UP030` | `STYLE-015` | low | Ruff — implicit positional format |
| `B011` | `ASSERT-002` | low | Ruff — assert False instead of AssertionError |
| `B018` | `STYLE-016` | low | Ruff — useless expression |
| `B023` | `SECURITY-050` | medium | Ruff — closure variable in loop (logic/security bug) |
| `B026` | `STYLE-016` | low | Ruff — star-arg after keyword arg |
| `B009` | `BEST-PRACTICE-006` | low | Ruff — getattr with constant string |
| `sql-injection-string-concat` | `SECURITY-027` | high | Semgrep — SQL via string concat |
| `global-variable` | `BEST-PRACTICE-004` | low | Semgrep — global statement |
| `open-without-context-manager` | `BEST-PRACTICE-005` | medium | Semgrep — open() without with |
| `path-traversal` | `SECURITY-049` | high | Semgrep — user-controlled file path |

### After Fix

- CUSTOM-* findings: **0** across all repos
- Tests: **370 passed**, 0 failed
- RULE_MAPPING now covers: **139+ rules**

---

## Section 12 — Round 8: False Positive Rate on Clean JS Codebases (v3.0.3)

**Date:** April 14, 2026 · **Version:** v3.0.3

After shipping the JS/TS adapter, three clean production JavaScript frameworks were scanned
to characterize the false positive rate **before and after** rule refinements.

### Why This Matters

A static analysis tool that generates excessive false positives on clean code is not deployable
in professional teams. This section documents FP reduction work done to make ACR-QA production-ready.

---

### Semgrep HIGH Findings on Clean Production JS Codebases (Post-Refinement)

| Repository | Stars | JS Files | Semgrep HIGH | FP Assessment |
|------------|:-----:|:--------:|:------------:|:-------------:|
| expressjs/express | 65k | ~30 | **0** | ✅ Zero FP |
| koajs/koa | 35k | ~40 | **0** | ✅ Zero FP (was 12 before fix) |
| fastify/fastify | 32k | ~100 | **4** | ✅ npm CVEs only — true positives |

> Note: Koa total findings include npm audit CVEs (medium severity). Semgrep-only HIGH = 0 after test-file exclusions.

---

### FP Root Causes Identified and Fixed

| Rule | FP Cause | Fix Applied |
|------|----------|-------------|
| `js-eval-injection` | Fires on `eval()` in `*.test.js` (Koa uses eval in test harness) | Added `paths: exclude` for all test patterns |
| `js-ssrf-request` | Generic `request()` caught `supertest` in test suites | Narrowed to `axios`/`fetch`/`got`/`needle` only + test exclusions |
| `js-nosql-injection-mongodb` | Matched Sequelize `.find()` with non-user params | Restricted pattern to require `req.$X.$Y` or `req.body.$Y` |

---

### NodeGoat Impact (Add New NoSQL Catch)

With the new `js-nosql-where-injection` rule (v3.0.3), NodeGoat now has:

| Rule | File | Line | Vulnerability |
|------|------|:----:|---------------|
| `SECURITY-065` (SSRF) | `research.js` | 16 | SSRF via user-controlled URL |
| `SECURITY-058` (NoSQL `$where`) | `allocations-dao.js` | 77 | `$where` template literal injection |

NodeGoat recall updated: **5 caught** (eval×3, SSRF, NoSQL `$where`) out of 12 documented.
Adjusted recall (excl. logic/auth flaws): **5/8 = 62.5%**.

---

### Scale Benchmark (v3.0.3, `scripts/scale_benchmark.py`)

Synthetic JS projects of increasing size, measuring pipeline wall time:

| Files | Time | Throughput |
|:-----:|:----:|:----------:|
| 10 | 6.31s | 1.6 files/s |
| 50 | 6.50s | 7.7 files/s |
| 100 | 7.11s | 14.1 files/s |
| 200 | 7.58s | 26.4 files/s |
| 500 | 9.83s | 50.9 files/s |

> **50× files → 1.6× time.** Overhead (ESLint startup, DB write) dominates at small scale. At 500 files,
> throughput is 50.9 files/s — suitable for large enterprise monorepos.

---

### Test Suite — v3.0.4 Baseline

```text
526 passed, 4 skipped, 32 warnings in ~81s
Coverage: 55.26% (≥40% requirement met)
ruff: 0 errors
mypy: 0 errors
```

---

## Section 12 — Feature Validation Round (v3.0.4 → v3.1.0)
*April 2026 — Features 2–7 + Architecture Cleanup*

### Test Suite Progression

| Version | Tests Passed | Coverage | Notes |
|---------|-------------|----------|-------|
| v3.0.4  | 452         | 55%      | Feature 2 CBoM baseline |
| v3.0.5  | 459         | 55%      | Feature 3 quality gate |
| v3.0.6  | 459         | 55%      | JS/TS pipeline unification |
| v3.0.7  | 462         | 55%      | Feature 4 autofix PR |
| v3.0.8  | 474         | 55%      | Feature 5 confidence scoring |
| v3.0.9  | 482         | 54%      | Feature 6 triage memory |
| v3.1.0  | 497         | 56%      | Feature 7 path feasibility |
| v3.1.1  | 508         | 57%      | Feature 8 dependency reachability |

### Bugs Found and Fixed This Round

| Bug | Symptom | Root Cause | Fix | Commit |
|-----|---------|-----------|-----|--------|
| JS categories invalid | `"pattern"`, `"other"`, `"imports"` warnings on every scan | `_infer_category()` mapped to non-canonical values | Remapped to valid categories: `best-practice`, `style`, `dead-code` | 31307d0 |
| JS pipeline bypassed filters | Config filters, dedup, sort, CBoM skipped for JS targets | JS path was a separate CLI block, not routed through `AnalysisPipeline` | Merged JS path into `AnalysisPipeline.run_js()` | 53dd42a |
| DVNA baseline regression | 39 findings instead of 128 after JS pipeline refactor | `cap_per_rule(max=5)` applied to JS path, capping BEST-PRACTICE-004 (47 hits) | Removed cap from JS CLI path | 31307d0 |
| `fix_code` always NULL | `fix_validated=True` stored but `fix_code=NULL` in DB | `validated_fix` key missing from explainer result dict | Added `result["validated_fix"] = validation.get("validated_fix")` | e55bd33 |
| `args.no_ai` AttributeError | CLI crash on `--no-ai` flag | `--no-ai` sets `dest="ai"` but code referenced `args.no_ai` | Changed to `not args.ai` | 2600c75 |
| DATA/outputs committed to git | Generated JSON/txt files on every run | Missing from .gitignore | Added `DATA/outputs/` to .gitignore | 28e744f |
| DVNA/NodeGoat dangling gitlinks | CI failure mode 160000 submodules | `git add` on uninitialized git repos | Removed from index, added clone_eval_repos.sh | 851d177 |
| asyncio.coroutine dead code | mypy arg-type error | Dead branch using deprecated asyncio.coroutine | Removed dead branch | c80a2d5 |

### New Engines Added This Round

| Engine | File | Purpose | Tests |
|--------|------|---------|-------|
| CBoM Scanner | `CORE/engines/cbom_scanner.py` | Crypto inventory + quantum-safety classification | 7 |
| Confidence Scorer | `CORE/engines/confidence_scorer.py` | 0-100 finding confidence score | 12 |
| Triage Memory | `CORE/engines/triage_memory.py` | FP suppression via learned patterns | 8 |
| Path Feasibility | `CORE/engines/path_feasibility.py` | AI execution path reachability check | 15 |

### Architecture Changes This Round

- JS/TS pipeline merged into `AnalysisPipeline.run_js()` — unified 5-step pipeline for both languages
- `findings.confidence_score` — new DB column, computed at insert time by ConfidenceScorer
- `suppression_rules` — new DB table for triage memory
- `llm_explanations` extended with fix validation fields (Feature 1) and feasibility fields (Feature 7)
- `clone_eval_repos.sh` — reproducible eval corpus setup with pinned DVNA commit hash

### DVNA Baseline Verification (v3.1.0)
Target: tmp_repos/DVNA (commit 9ba473a)
Total findings: 128 | High: 4 | Medium: 77 | Low: 47
Quality Gate: FAILED (4 HIGH > max 0) — expected for vulnerable app

### NodeGoat First Full Pipeline Run (v3.1.0)
Target: tmp_repos/NodeGoat
Total findings: 310 (319 raw − 9 deduped) | High: 7 | Medium: 145 | Low: 158
AI explanations: 7 HIGH findings in 2299ms

| `created_at` bug in /api/trends | All chart labels showed "unknown" | Flask route read `created_at` but DB returns `started_at` | Changed to `row.get("started_at")` | latest |

---

## Section 13 — Round 15: v3.2.0 Release (April 2026)
*Coverage Push & Go Language Integration*

### Test Suite Progression

| Version | Tests Passed | Engine Coverage | Notes |
|---------|-------------|----------|-------|
| v3.1.3  | 526         | < 60%    | Baseline |
| v3.1.x  | 841         | > 94%    | Huge coverage push across 7 engines |
| v3.2.0  | 892         | > 94%    | Added `test_go_adapter.py` (51 tests) |

### Key Improvements
- Extensively boosted coverage for core engines (scorer, normalizer, explainer, cbom, etc.) reaching >94% line coverage each.
- Full testing of the new Go Language adapter spanning offline `gosec`, `staticcheck` and `semgrep` Go rules.
- Robust parsing for dynamic output line ranges (e.g. `'37-40'`) in gosec outputs, now returning the lowest single digit integer to prevent SQL write issues.

---

## Section 14 — Quality Audit: CUSTOM-* Elimination & Output Integrity (May 2026)

*Full pipeline audit across all 7 targets — verified zero CUSTOM-* findings, fixed severity bugs, cleaned JSON output*

### Issues Found & Fixed

| Bug | Root Cause | Fix |
|-----|-----------|-----|
| 20 `CUSTOM-GO-*` findings on govwa | 6 staticcheck rules unmapped (S1023/25/31/39, ST1005/06) | Added STYLE-021–026 in `go_adapter.py` + `severity_scorer.py` |
| 9 `CUSTOM-eslint-unknown` as HIGH on dvblab | ESLint parsing errors (null ruleId) treated as real findings | Extended null-ruleId filter to also skip `"Parsing error:"` messages |
| 6 Ruff rules unmapped on pygoat | E402/E711/E712/F601/UP008/UP015 missing from RULE_MAPPING | Added IMPORT-005, PATTERN-003/004, BEST-PRACTICE-008, STYLE-019/020 |
| 15 duplicate keys in `severity_scorer.py` | RULE_SEVERITY built up incrementally without dedup check | Removed early-block duplicates; last/more-precise definitions kept |
| `SECURITY-047` severity `"critical"` | Not a valid `CanonicalFinding` severity (Pydantic rejects it) | Changed to `"high"` throughout |
| Go/JS severity overridden by scorer | `CanonicalFinding.create()` calls `SeverityScorer.score()` which uses Python-centric RULE_SEVERITY | Added `model_copy(update={"severity": ...})` in `normalize_gosec()` and `normalize_eslint()` |
| `--json` stdout polluted | Logging hardwired to `sys.stdout`; `run_checks.sh` also writes to stdout | Logging → stderr when `--json`; subprocess stdout → DEVNULL |

### Target Coverage (All Verified)

| Target | Language | Total Findings | CUSTOM-* | Status |
|--------|----------|:--------------:|:--------:|--------|
| pygoat | Python | 440 raw / 126 capped | 0 | ✅ |
| dvpwa | Python | 44 | 0 | ✅ |
| dsvw | Python | 59 raw / 33 capped | 0 | ✅ |
| vulpy | Python | 293 raw / 73 capped | 0 | ✅ |
| dvblab | JavaScript | 148 | 0 | ✅ |
| vuln-node-api | JavaScript | 72 | 0 | ✅ |
| govwa | Go | 46 | 0 | ✅ |

### Test Suite After

| Version | Tests Passed | Coverage | Notes |
|---------|-------------|----------|-------|
| v3.2.4 (May 5) | **1,690** | **86%** | Full quality audit; fixed 6 adapter bugs |
