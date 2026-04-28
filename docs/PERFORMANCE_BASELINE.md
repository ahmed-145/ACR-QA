# ACR-QA Performance Baseline

**Date:** 2026-03-04 · **Commit:** `278f69f` · **Environment:** Ubuntu Linux, Python 3.11, Docker

## Test Configuration

- **Target:** `TESTS/samples/comprehensive-issues/` (11 Python files, ~800 lines)
- **Tools:** Ruff, Semgrep, Vulture, jscpd, Radon, Bandit + Secrets Detector + SCA Scanner
- **AI:** Groq Llama 3.1 8B (free tier), 3 explanations

## Pipeline Timings

| Phase | Duration |
|-------|----------|
| Rate limit check | <100ms |
| DB run creation | <100ms |
| Detection (6 tools) | ~8s |
| Extra scanners (secrets + SCA) | ~2s |
| Normalization + dedup | <500ms |
| AI explanation (per finding) | 400-1400ms |
| Quality gate evaluation | <10ms |
| **Total (3 explanations)** | **~14s** |

## Detection Results

| Metric | Value |
|--------|-------|
| Raw findings | 417 |
| After dedup | 387 (30 duplicates removed, 7.2%) |
| High severity | 3 |
| Medium severity | 19 |
| Low severity | 365 |
| Security findings | 5 |
| Secrets detected | 2 |

## AI Explanation Latency

| Call | Latency | Rule |
|------|---------|------|
| 1 | 1391ms | CUSTOM-D205 |
| 2 | 599ms | CUSTOM-D212 |
| 3 | 409ms | CUSTOM-D400 |
| **Mean** | **800ms** | |

## Test Suite

| Metric | Value |
|--------|-------|
| Total tests | **526** (as of v3.1.3) |
| Passed | **436** |
| Skipped | 4 (infrastructure-dependent) |
| Runtime | ~6s |
| `quality_gate.py` coverage | **93%** |
| `severity_scorer.py` coverage | **62%** |

## Resource Usage

| Resource | Value |
|----------|-------|
| Python source lines | 11,167 |
| Docker services | 5 (PostgreSQL, Redis, App, Prometheus, Grafana) |
| DB tables | 5 |
| API endpoints | 20 |
| Rule mappings | 97 |

## Notes

- Redis was unavailable during this test (graceful degradation to in-memory rate limiting)
- AI explanation latency varies with Groq API load (first call always slowest due to TCP warming)
- Quality gate correctly failed for test samples (intentional issues)
- Dedup removed 7.2% of findings (same file+line+rule from different tools)

## v2.9 Updates Since This Baseline

| Change | Before | After |
|--------|--------|-------|
| Test count | 97 | **436** |
| `quality_gate.py` coverage | ~38% | **93%** |
| `severity_scorer.py` coverage | ~25% | **62%** |
| SECURITY-008 (pickle) severity | medium | **high** (CWE-502) |
| SECURITY-018 (yaml.load) severity | medium | **high** (CWE-502) |
| CUSTOM-* findings in output | 3 types | **0** |
| PR comment file paths | `/tmp/pr-files/` prefix | Clean relative paths |
| Rule mappings | 97 | 127 |

**Pipeline timing unchanged** — normalization and severity scoring are pure in-memory operations; the new test coverage does not affect runtime performance.

---

## v3.1.0 Baseline (April 2026)

| Metric | Value |
|--------|-------|
| Test suite | 497 passed, 4 skipped |
| Coverage | 56% |
| DVNA findings | 128 (stable across all versions) |
| NodeGoat findings | 310 |
| AI batch latency (4 HIGH findings) | ~1300ms |
| AI batch latency (7 HIGH findings) | ~2300ms |
| Feasibility check latency | ~80-150ms per finding |
| Confidence scoring | <1ms per finding (no network call) |
| Triage memory suppression check | <5ms per finding (single DB query) |
| Feature 8 reachability check | <2ms per npm finding (regex scan, cached) |

| Feature 9 cross-language correlation | <10ms per project scan (regex + file scan, cached) |
| Feature 10 trend API | <50ms per request (single PostgreSQL aggregation query) |
