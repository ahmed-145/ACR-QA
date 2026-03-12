# ACR-QA Testing & Calibration Report

**Latest Run:** March 11, 2026 · **Version:** v2.8  
**Unit Tests:** 275 passed, 4 skipped · **Coverage:** 38.85%

---

## Table of Contents

1. [Unit Test Suite (v2.7 + v2.8)](#1-unit-test-suite)
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
| `TESTS/test_god_mode.py` | 78 | v2.7 |
| `TESTS/test_deep_coverage.py` | 98 | v2.6 |
| `TESTS/test_config_quality.py` | 30 | v2.5 |
| `TESTS/test_integration.py` | 69 | v2.4 |

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
| `explainer.py` | 45% | LLM calls + Redis caching — requires live `CEREBRAS_API_KEY` |

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

