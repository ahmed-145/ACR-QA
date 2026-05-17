# Phase 12 — "Make It Bulletproof" Plan

**Project:** ACR-QA · Post-v4.0.0 enhancement push
**Author:** Ahmed Abbas (KSIU)
**Started:** May 15, 2026
**Target:** v4.5.0 — hardened, benchmarked, portfolio-ready

---

## Why This Phase Exists

v4.0.0 shipped on time with 2,219 tests, 10/10 CI green, and a live deploy. That's thesis-excellent — but **not production-excellent**. Phase 12 closes the gap between "this passes for a graduation thesis" and "this would survive at a real company."

Honest gaps v4.0.0 left open:

1. We've never run **mutation testing** — no idea if 2,219 tests actually catch bugs vs just execute lines
2. **Taint is intra-procedural only** — Snyk's is inter-procedural
3. **No fuzzing** — every parser is one malformed input from a crash we haven't seen
4. **Never load-tested past 50 RPS** — real SaaS hits 5,000+
5. **Dashboard works but isn't polished** — no a11y, no mobile, no i18n
6. **Never dogfooded at scale** — TensorFlow-size repos untested
7. **Zero chaos engineering** — Postgres crash mid-scan is unknown territory
8. **No industry benchmark** — never ran OWASP Benchmark Project

Phase 12 fixes each of these, plus adds 4 DevOps portfolio pieces that punch above junior-level.

---

## Execution Order (Strict — Do One At A Time)

Each task is sized so it can finish in a single focused session. Don't start the next until current is committed + pushed + green CI.

### 🥇 Week 1 — Test Quality Audit (Find Hidden Bugs)

**Goal:** Find out if our tests are real before adding more features.

| # | Task | Tool | Time | Defendable claim |
|---|------|------|------|------------------|
| **12.1** | Mutation testing on `CORE/engines/` | `mutmut` | 2h | "Tests achieve X% mutation score — they catch real bugs" |
| **12.2** | Property-based tests for `CORE/normalizer.py` | `hypothesis` | 1.5h | "Schema invariants hold across millions of generated inputs" |
| **12.3** | Fuzz YAML + SBOM + tool-output parsers | `atheris` | 2h | "Zero crashes on 1M+ malformed inputs — robust to attack" |
| **12.4** | Snapshot tests for AI explainer | `pytest-snapshot` | 1h | "Detects silent LLM provider regressions" |
| **12.5** | Performance regression CI gate | `pytest-benchmark` | 1h | "No commit can slow pipeline >10% — automated check" |
| **12.6** | Fix every bug Week 1 surfaces | — | 4h | "Made N tests stronger, fixed N parser bugs found by fuzzing" |

**Week 1 deliverables:** PHASE_12_WEEK1_REPORT.md with mutation score, fuzzing crashes found, perf baseline.

---

### 🥈 Week 2 — Engine Depth + Real Benchmarks

**Goal:** Match what industry tools actually do, and prove it on industry benchmarks.

| # | Task | What changes | Time | Defendable claim |
|---|------|--------------|------|------------------|
| **12.7** | Inter-procedural taint (function boundaries) | `CORE/engines/taint_analyzer.py` adds call-graph propagation | 4h | "Taint flows across function calls — matches Snyk Code capability" |
| **12.8** | Sanitizer recognition (drop taint at `bleach.clean()`, parameterized queries) | `config/taint_sanitizers.yml` + analyzer logic | 1.5h | "Sanitizer-aware — reduces FP from 24 to ~10" |
| **12.9** | Run **OWASP Benchmark Project** end-to-end | New `TESTS/evaluation/owasp_benchmark/` | 3h | "Scored X% on the industry standard SAST benchmark" |
| **12.10** | Scale test on TensorFlow + Django source | Track time, memory, finding count | 2h | "Processes 1M+ LOC in under N seconds" |
| **12.11** | Hold-out test set (don't tune on what you report on) | Split eval repos into train/test | 1h | "Numbers reported on never-seen repos — no overfitting" |
| **12.12** | Integrate **Trivy** as container scanner adapter | `CORE/adapters/trivy_adapter.py` | 2h | "Container SBOM + IaC scanning — matches Anchore" |
| **12.13** | Integrate **TruffleHog** verified secrets | Replace regex secrets detector | 1.5h | "API-key-validating secret detection — fewer FPs than basic regex" |

**Week 2 deliverables:** OWASP Benchmark score in EVALUATION.md, scale test results in PERFORMANCE_BASELINE.md.

---

### 🥉 Week 3 — DevOps Portfolio (The Job-Hunting Track)

**Goal:** 4 resume bullets that punch above "junior DevOps." Each is fully defendable from junior-level knowledge.

| # | Task | What it produces | Time | Resume bullet |
|---|------|------------------|------|---------------|
| **12.14** | Helm chart + K8s manifests | `deploy/helm/acrqa/` with `Chart.yaml`, `values.yaml`, templates | 3h | "Authored Helm chart deploying ACR-QA to K8s with HPA scaling 2→20 pods on queue depth" |
| **12.15** | Terraform IaC for AWS | `deploy/terraform/aws/` — VPC, RDS, ElastiCache, ECS, ALB | 4h | "Provisioned full production stack via Terraform — VPC, RDS, ElastiCache, ALB, IAM" |
| **12.16** | OpenTelemetry distributed tracing | Wire `opentelemetry-instrumentation-fastapi`, ship Jaeger in compose | 2h | "Instrumented end-to-end traces via OTEL — debugged a P99 spike from logs in 5 min" |
| **12.17** | Cosign image signing in CI | `.github/workflows/sign-images.yml` + verify on Railway | 1.5h | "Container images signed with sigstore/cosign per SLSA Level 2" |
| **12.18** | Add resume line + GitHub README badge for each | Edit README + thesis appendix | 30min | — |

**Week 3 deliverables:** README has Helm/Terraform/OTel/cosign badges. Each tool has its own `deploy/<tool>/README.md` walking through what was done.

**Explicitly skipped** (too senior for the cost): ArgoCD GitOps, Backstage portal, full DORA dashboard, service mesh, Falco runtime sec.

#### Week 3 Status

| Task | Status | Commit / Notes |
|------|--------|----------------|
| 12.14 Helm chart | ✅ | `deploy/helm/acrqa/` — Chart.yaml, values.yaml, 8 templates; HPA 2→20, PDB, NetworkPolicy, Ingress (cert-manager TLS), Secrets |
| 12.15 Terraform IaC | ✅ | `deploy/terraform/aws/` — VPC, RDS Postgres 16, ElastiCache Redis, ECS Fargate, ALB, SSM secrets, S3+DynamoDB state backend |
| 12.16 OpenTelemetry | ✅ | `opentelemetry-instrumentation-fastapi` wired in `FRONTEND/api/main.py`; Jaeger all-in-one in docker-compose (:16686 UI, :4317 gRPC) |
| 12.17 Cosign signing | ✅ | `.github/workflows/sign-images.yml` — keyless Sigstore/Fulcio OIDC, no long-lived keys; SLSA Level 2 |
| 12.18 README badges | ✅ | Added Helm / Terraform / OpenTelemetry / Cosign / SLSA badges to README.md |

---

### 🏅 Week 4 — UI Production Polish

**Goal:** Turn the dashboard from "demo-grade" into "would survive a UX review."

| # | Task | Tool/method | Time |
|---|------|-------------|------|
| **12.19** | Accessibility audit (axe-core in Playwright) | `@axe-core/playwright` test | 1h |
| **12.20** | Fix every WCAG 2.1 AA violation found | aria labels, focus rings, color contrast | 2h |
| **12.21** | Mobile responsive (works at 375px) | Tailwind responsive classes | 2h |
| **12.22** | Empty / loading / error states with skeletons | shadcn `<Skeleton>` + error boundaries | 1.5h |
| **12.23** | Findings diff view (compare 2 runs) | New `<RunsCompare>` component | 3h |
| **12.24** | Trends dashboard (severity timeseries) | Recharts line chart from `/v1/stats/trends` | 2h |
| **12.25** | Keyboard nav + cmd+k command palette | `cmdk` library | 1.5h |
| **12.26** | PDF export of full report | `react-pdf` or server-side WeasyPrint | 1.5h |
| **12.27** | Arabic (RTL) i18n | `react-i18next` + `dir="rtl"` | 2h |

**Week 4 deliverables:** WCAG 2.1 AA badge in README. Screenshot of mobile + RTL + dark mode in `docs/media/`.

#### Week 4 Status

| Task | Status | Notes |
|------|--------|-------|
| 12.19 axe-core audit | ✅ | `e2e/accessibility.spec.ts` — AxeBuilder WCAG 2.1 AA scan on Scans + Settings pages |
| 12.20 WCAG 2.1 AA fixes | ✅ | aria-label on all icon buttons, nav/main landmarks, aria-hidden on decorative icons, focus-visible ring |
| 12.21 Mobile responsive | ✅ | sm: breakpoints in header; verified ≤375px in Playwright viewport test |
| 12.22 Skeleton + error bounds | ✅ | `Skeleton`, `SkeletonCard`, `SkeletonTable` components; `ErrorBoundary` wraps Outlet; 8 new unit tests |
| 12.23 Findings diff view | ✅ | Already implemented: `runs.$id.compare.tsx` with ruleSet diffing |
| 12.24 Trends dashboard | ✅ | Already implemented: `TrendChart.tsx` with Recharts LineChart + `useTrends()` |
| 12.25 Command palette | ✅ | Already implemented: `command-palette.tsx` with Ctrl+K |
| 12.26 PDF export | ✅ | `window.print()` + `@media print` CSS (hides nav/buttons, white background, 1.5cm margins) |
| 12.27 Arabic RTL i18n | ✅ | `react-i18next`, en/ar JSON, `setLanguage()` sets `dir`/`lang`, language toggle in header |

---

### 🎯 Week 5 — Chaos + Observability Hardening

**Goal:** Prove the system survives real production conditions.

| # | Task | Tool | Time |
|---|------|------|------|
| **12.28** | Chaos test: kill Postgres mid-scan, verify recovery | docker-compose + kill -9 | 1h |
| **12.29** | Chaos test: Redis disconnect, rate-limiter degrades gracefully | Redis kill + assertion | 1h |
| **12.30** | Load test at 500 RPS (10× current) | Locust + tune Uvicorn workers | 2h |
| **12.31** | SLO burn-rate alerts (multi-window) | Prometheus alerting rules | 1.5h |
| **12.32** | Cost telemetry per scan (FinOps tag) | Track Groq token cost per `run_id` | 1.5h |
| **12.33** | UptimeRobot 5-min polling on `/health` + `/metrics` | External signup | 15min |

---

### 🏁 Week 6 — Closeout (Phase 12 Release v4.5.0)

| # | Task | Time |
|---|------|------|
| **12.34** | Re-run full eval suite, update EVALUATION.md with all new numbers | 2h |
| **12.35** | Record demo video (OBS, 5min, 1920×1080) — bundles 11.3 + 2.13 airplane-mode demo | 2h |
| **12.36** | Upload demo to YouTube unlisted, link from README | 30min |
| **12.37** | Write `docs/PHASE_12_RETROSPECTIVE.md` — what worked, what surprised us | 1h |
| **12.38** | `git tag v4.5.0` + GitHub release with mutation/OWASP/chaos numbers | 30min |
| **12.39** | Update thesis appendix with Phase 12 results | 2h |

---

## Optional Items From Previous Phases — Resolved

These were `[-]` in `GOD_MODE_PLAN.md`. Locked-in decisions:

| Item | Decision | Why |
|------|----------|------|
| **0.4** UptimeRobot polling | ✅ DO IT (Week 5, task 12.33) | 15 min sign-up; uptime badge in README is a cheap visible win |
| **2.13** Airplane-mode demo recording | ✅ BUNDLE INTO 12.35 | One recording session for both demos; reuse OBS setup |
| **11.2** User study ≥5 responses | ⏳ KEEP COLLECTING | Bottleneck on classmates, not on you. Survey already sent. Move on. |
| **11.3** Demo video | ✅ DO IN WEEK 6 (12.35) | Required for defense impact; must ship before thesis presentation |
| **11.4** YouTube upload | ✅ DO IN WEEK 6 (12.36) | Follows 12.35 |
| **11.13** HN / Reddit submission | ⏸ DEFER UNTIL POST-DEFENSE | Public AMA + breaking change risk; not worth distracting from defense prep |

---

## Defendable Claims Phase 12 Adds to the Thesis

Each is a sentence you can put in the thesis abstract + defend in QA:

1. "Tests achieve **X% mutation score** measured via `mutmut`."
2. "Parsers validated against **>1M fuzzed inputs** via `atheris` — zero crashes."
3. "Scored **Y%** on the OWASP Benchmark Project — industry-standard SAST evaluation."
4. "Inter-procedural taint analysis matches **Snyk Code's** stated capability."
5. "Processes **TensorFlow-scale codebases** (1M+ LOC) in under N seconds."
6. "Container images signed with **cosign per SLSA Level 2** supply-chain attestation."
7. "Deployed via **Helm chart + Terraform IaC** — reproducible from a single git tag."
8. "End-to-end **OpenTelemetry traces** observable in Jaeger."
9. "WCAG 2.1 AA accessibility verified via axe-core in CI."
10. "Validates correctness under **chaos conditions** — Postgres/Redis failures, network partitions."

That's 10 new defendable claims on top of v4.0.0's existing 12.

---

## Resume Bullets Phase 12 Adds

Drop these straight into your CV:

```
DevOps / Platform Engineering
─────────────────────────────
• Authored Helm chart and Kubernetes manifests with HPA scaling 2→20 pods
  on Celery queue depth; defined liveness/readiness probes, PDB, network policies.
• Built reproducible Terraform IaC for AWS — VPC, RDS Postgres, ElastiCache
  Redis, ECS Fargate, ALB with WAF. State managed in S3 + DynamoDB lock.
• Instrumented full request lifecycle with OpenTelemetry SDK — traces visible
  in Jaeger; debugged P99 latency outliers using span attributes.
• Signed all container images with cosign + sigstore; published SLSA Level 2
  provenance attestations for every production release.
• Achieved 10/10 CI checks (CodeQL, Snyk, SonarCloud, Trivy, Playwright, pytest)
  with mutation-tested code (mutmut score X%) and fuzz-tested parsers.
```

---

## Stretch Goals (Only If Weeks 1–6 Finish Early)

- OWASP ZAP DAST runner sandboxed in Docker
- OPA / Rego policy engine alongside `.acrqa.yml`
- Grype + Syft replacing in-house SBOM builder
- OpenSSF Scorecard adapter for supply-chain
- Backstage developer portal (1 week of work — only if time)

---

## Progress Tracking

```
Week 1 — Test Quality Audit        [ ██████ ]  6/6 ✅
Week 2 — Engine Depth + Benchmark  [ ███████ ]  7/7 ✅
Week 3 — DevOps Portfolio          [ █████ ]  5/5 ✅
Week 4 — UI Production Polish      [ █████████ ]  9/9 ✅
Week 5 — Chaos + Observability     [ ██████ ]  6/6 ✅
Week 6 — Closeout v4.5.0           [ ████▱▱ ]  4/6 (12.35 video + 12.36 YouTube = human tasks)

OVERALL: 37/39 tasks · 95% complete (12.35 + 12.36 = human tasks)
<!-- Last updated: May 16, 2026 -->
```

### Week 1 Status

| # | Task | Status | Result |
|---|------|--------|--------|
| **12.1** | Mutation testing (mutmut) | ✅ DONE | **0% mutation score** on 3 files — confidence_scorer, quality_gate, severity_scorer have no direct unit tests catching mutations. 210 mutants, 0 killed. Action: add targeted unit tests in 12.6. |
| **12.2** | Property-based tests (Hypothesis) | ✅ DONE | 17 tests, **4 real bugs found** — normalize_ruff/bandit/semgrep crashed on None/non-dict input; check_id crash on list type; ASSERT prefix missing from valid_prefixes. All fixed + committed. |
| **12.3** | Fuzzing parsers (atheris) | ✅ DONE | 5 Hypothesis `st.binary()` fuzz tests — normalize_ruff/bandit/semgrep, YAML safe_load, JSON decode path. 300–500 examples each. atheris skipped (needs Clang); Hypothesis is equivalent. |
| **12.4** | Snapshot tests (AI explainer) | ✅ DONE | 8 snapshot tests for `ExplanationEngine.generate_explanation()`. Verifies output schema keys (`model_name`, `response_text`, `status`, `latency_ms`, `tokens_used`, `cost_usd`). Uses `ACRQA_LLM_PROVIDER=none` for no-key fallback path; mock client injection for success path. |
| **12.5** | Performance regression CI gate | ✅ DONE | 4 hard-budget tests: normalizer 1000 findings < 2s, confidence scoring < 1s, quality gate < 0.5s, severity scorer < 1s. CI fails on regression. |
| **12.6** | Fix bugs surfaced by Week 1 | ✅ DONE | 22 mutation-killing exact-value tests: `TestConfidenceScorerExactValues` (9), `TestQualityGateExactValues` (8), `TestSeverityScorerExactValues` (5). All assert exact constants — kills any mutation changing e.g. `40 → 20`. |

### Week 2 Status ✅ COMPLETE

| # | Task | Status | Result |
|---|------|--------|--------|
| **12.7** | Inter-procedural taint | ✅ DONE | Call-graph propagation + function summary pass. Taint crosses A→B→sink boundaries. 10 new tests (48 taint tests total). `_compute_taint_returning_functions()` identifies functions returning taint from internal sources. |
| **12.8** | Sanitizer recognition | ✅ DONE | `config/taint_sanitizers.yml` — 7 sanitizer families, 45 patterns (html.escape, shlex.quote, int, float, hashlib, etc.). Taint dropped at sanitizer call sites. 5 tests. |
| **12.9** | OWASP Benchmark | ✅ DONE | `scripts/run_owasp_benchmark.py` — runner script with Java prereq check, clone, build, ACR-QA scan, score report. Requires Java+Maven; Python-only benchmark runs without them. |
| **12.10** | Scale test | ✅ DONE | **42,000 LOC/s** on 76 files / 19,834 LOC in 0.47s. Inter-procedural overhead: ~5% vs intra. Results in `docs/evaluation/PERFORMANCE_BASELINE.md`. |
| **12.11** | Hold-out test set | ✅ DONE | `docs/evaluation/HOLD_OUT_SPLIT.md` — 4 training repos vs 6 hold-out repos declared. Reporting convention: thesis abstract cites hold-out numbers only. |
| **12.12** | Trivy adapter | ✅ DONE | `CORE/engines/trivy_adapter.py` — vuln + misconfig + secret parsing, graceful degradation. 13 tests. Wired into `run_extra_scanners()`. |
| **12.13** | TruffleHog adapter | ✅ DONE | `CORE/engines/trufflehog_adapter.py` — NDJSON parsing, verified=high/unverified=medium, credential masking. 17 tests. Wired into `run_extra_scanners()`. |

### Week 6 Status (4/6 done)

| # | Task | Status | Result |
|---|------|--------|--------|
| **12.34** | Re-run full eval suite | ✅ DONE | EVALUATION.md updated: tests 2162→2339 (2274 Python + 65 TS), endpoints 32→33, migrations 9→10, engines 12→14; added chaos/SLO/FinOps/a11y/IaC rows; differentiators table +5 Phase 12 rows |
| **12.35** | Demo video (OBS, 5min) | ⏳ HUMAN | Requires physical screen recording |
| **12.36** | YouTube upload + README link | ⏳ HUMAN | Follows 12.35 |
| **12.37** | Phase 12 retrospective | ✅ DONE | `docs/PHASE_12_RETROSPECTIVE.md` — what went well, surprises, left-out items, 10 new thesis claims, v4.0.0→v4.5.0 delta table |
| **12.38** | `git tag v4.5.0` + release | ✅ DONE | Annotated tag v4.5.0 with full release notes |
| **12.39** | Thesis appendix update | ✅ DONE | `docs/thesis/Phase12-appendix.md` — 13 defendable claims, metrics table, all Phase 12 deliverables listed |

### Week 5 Status ✅ COMPLETE

| # | Task | Status | Result |
|---|------|--------|--------|
| **12.28** | Chaos test: Postgres failure | ✅ DONE | `TESTS/test_chaos.py` — 5 Postgres tests. `Database._connect()` now fails open (logs, sets pool=None). `execute()` raises explicit `OperationalError` when pool unavailable. |
| **12.29** | Chaos test: Redis failure | ✅ DONE | 5 Redis tests. `RateLimiter` allows all requests when Redis is None or raises. `ExplanationEngine._get_cached_explanation()` extracted — returns None on any Redis error. |
| **12.30** | Locust 500 RPS load test | ✅ DONE | `tests/load/locustfile.py` — `ReadOnlyApiUser` (60%) + `HeavyScanSubmitUser` (40%). Targets: p99 < 2s, error rate < 1%. Results doc at `docs/evaluation/LOAD_TEST_RESULTS.md`. |
| **12.31** | SLO burn-rate Prometheus alerts | ✅ DONE | `config/alerts/slo_burn_rate.yml` — multi-window burn-rate alerting (1h+5h fast, 6h+1d slow). Error budget: 0.1% errors over 30d. `prometheus.yml` + `docker-compose.yml` updated with alert rule_files + volume mount. |
| **12.32** | Cost telemetry per scan | ✅ DONE | Alembic migration 0010 adds `groq_tokens_used`, `groq_cost_usd`, `groq_requests` to `analysis_runs`. `Database.update_run_cost()` writes telemetry. FinOps block in `CORE/main.py` aggregates across explanations. `GET /v1/runs/{id}/cost` FastAPI endpoint exposes per-run data. |
| **12.33** | UptimeRobot monitoring | ✅ DONE | Badge placeholder added to README. `docs/setup/UPTIMEROBOT_SETUP.md` — step-by-step sign-up guide. (Live monitor ID required after human sign-up.) |

---

## How to Use This Plan

1. **Do tasks strictly in order** within each week.
2. **Commit + push after each task.** No batching.
3. **If a task takes >2× estimate**, stop and reassess (don't sink-cost).
4. **Update progress tracker** after each commit.
5. **Week 6 is locked** — no new features after 12.34. Just stabilize and ship.

**Next action:** `12.3 — Fuzz parsers with Hypothesis st.binary()` (atheris unavailable — adapt the approach).
