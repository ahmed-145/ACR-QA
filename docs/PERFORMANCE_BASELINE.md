# ACR-QA Performance Baseline

**Last updated:** May 2026 · **Version:** v3.9.2 · **Environment:** Ubuntu 22.04, Python 3.11, Docker Compose (PostgreSQL 15 + Redis 7)

---

## v3.9.2 Baseline (May 2026 — Locust Load Test)

Target SLOs: **50 RPS sustained, p95 < 500ms, error rate < 1%**

Run:
```bash
locust -f TESTS/load/locustfile.py --headless -u 50 -r 5 -t 120s \
       --host http://localhost:8000
```

| Metric | Result | SLO | Status |
|--------|:------:|:---:|:------:|
| Peak RPS | 52 | ≥50 | ✅ |
| p50 latency | 38ms | — | — |
| p95 latency | 287ms | <500ms | ✅ |
| p99 latency | 412ms | — | — |
| Error rate | 0.3% | <1% | ✅ |

**FastAPI endpoint p95 latency (local):**

| Endpoint | p95 |
|----------|:---:|
| `GET /health` | 4ms |
| `GET /v1/runs?limit=20` | 28ms |
| `GET /v1/runs/{id}/findings` | 42ms |
| `POST /v1/scans` | 85ms |

**Scan pipeline timing (no LLM):**

| Repo | LOC | Scan time |
|------|----:|:---------:|
| DSVW | 150 | 3.8s |
| Flask 68k★ | 5,200 | 18.1s |

All three SLOs met at 50 RPS. Re-run against Railway deployment for production numbers.

---

## v3.2.4 Baseline (original)

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
| Total tests | **1,690** (as of v3.2.4) |
| Passed | **1,690** |
| Skipped | 13 (infrastructure-dependent) |
| Runtime | ~40s |
| `quality_gate.py` coverage | **95%** |
| `severity_scorer.py` coverage | **83%** |

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

## v3.2.4 Updates Since This Baseline

| Change | Baseline (v3.1.3) | Current (v3.2.4) |
|--------|--------|-------|
| Test count | 526 | **1,690** |
| `quality_gate.py` coverage | ~38% | **95%** |
| `severity_scorer.py` coverage | ~25% | **83%** |
| CUSTOM-* findings in output | multiple types | **0** (all targets) |
| Rule mappings | 97 | **311** |
| Languages supported | Python | Python, JS/TS, Go |
| `--json` stdout | polluted with progress | **clean JSON only** |
| Precision | 94.8% | **97.1%** |

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
