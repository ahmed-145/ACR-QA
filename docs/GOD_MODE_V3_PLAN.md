# ACR-QA God Mode Plan v3 — Road to v5.0.0

**Author:** Drafted May 18, 2026 — after v4.6.0 ship + competitive re-audit
**Status:** Active — supersedes `docs/GOD_MODE_PLAN.md` (v2, archived as complete)
**Owner:** Ahmed Mahmoud Abbas (KSIU, supervised by Dr. Samy AbdelNabi)
**Target version:** v5.0.0 (defense build) → v5.1.0 (public launch) → v6.0.0 (compound)
**Pace assumption:** 12 hr/day × 6 days = **~1.8× normal velocity** (sustainable; 16 hr/day is burnout math and is rejected)
**Defense date assumption:** Jun 25, 2026 (placeholder — Ahmed to confirm with Dr. Samy in Week A1; everything Week A4–A6 hard-anchored to this)

---

## 0. Executive Summary

ACR-QA v4.6.0 is feature-complete and defense-ready *on paper*. v3 of this plan answers a different question: **what gets us beyond defense-ready into industry-credible and recruiter-magnet territory, without crashing the defense in the process?**

The plan is split into three tiers with hard cut-lines between them:

- **Phase A (6 calendar weeks, May 18 – Jun 30):** Defense-perfect + 6 quantified resume bullets + v5.0.0-beta on PyPI. No public launch noise. No HN post.
- **Phase B (12 calendar weeks, Jul – Sep):** Public launch. Hosted SaaS at `acrqa.dev`. VSCode plugin. GitHub App. 100+ real users. v5.1.0 GA.
- **Phase C (24 calendar weeks, Oct – Mar 2027):** Compound. Conference talk or paper. OSS community. Optional PhD optionality. v6.0.0.

The four outside-the-box bets that distinguish ACR-QA from Snyk/Semgrep/SonarQube/CodeRabbit:

1. **Time-Travel Vulnerability Analysis** — bounded to last N commits; shows *when introduced*, *by whom*, *near-fixed-then-regressed* chains. Phase A Week 2.
2. **IaC Scanner** — Terraform + K8s + Dockerfile + GHA YAML. Competitive parity ships fast (checkov + kube-score + Semgrep). Phase A Week 2.
3. **PR Risk Score** — single 0–100 number for "should I merge this PR." Viral demo artifact. Phase A Week 5.
4. **Heuristic Risk Predictor** — explainable score per file using churn + complexity + test-gap + age + author count. **Not ML.** Documented features, defensible thesis claim. Phase A Week 3.

---

## 1. Honest Pace Model

| Variable | Value |
|---|---|
| Hours/day available | 12 |
| Days/week | 6 (Sunday off — non-negotiable) |
| Weekly hours | 72 |
| Normal full-time baseline | 40 |
| Velocity multiplier | **1.8×** |
| Calendar weeks in Phase A | 6 |
| Effective weeks of work | ~11 |
| Hard cap | Week A6 = polish only, **no new code** |

If a week runs long, the **Drop-First** list (per week below) is consulted before any defense-impacting task is touched.

---

## 2. Phase A — Defense + Job-App Sprint (6 weeks)

### Exit criteria for Phase A

By Jun 30, 2026, all of:

- ✅ Thesis defended (target Jun 25, ±5 days)
- ✅ v5.0.0-beta on PyPI (signed, OIDC, reproducible)
- ✅ Live hosted demo at `acrqa.dev/demo` (read-only DSVW scan, no auth)
- ✅ 6 quantified resume bullets (one per week)
- ✅ Updated paper draft: 8-page IEEE-style, intro + methodology + eval complete
- ✅ Updated thesis appendix: 28-repo eval corpus, κ ≥ 0.78, 4 new ADRs
- ✅ Quality gate against ACR-QA itself: 0 HIGH findings (dogfooded in CI)
- ✅ Security hardening pass: subprocess sandbox audit + secrets handling review + dep-confusion check

### Week A1 — May 18–24: UI Killshot (focused)

**Goal:** The dashboard becomes the defense demo's anchor visual. Four killer features only. Everything else slips.

**Tasks (in priority order):**

1. **AI Chat Sidebar per finding** — `/v1/findings/{id}/chat` SSE endpoint, conversation persisted in `finding_chat_messages` table (new migration 0012). UI: collapsible right-side panel on `finding.html` and React route, streaming Groq output with `<thinking>` tag rendering, four preset prompts (Explain, Show Exploit, Draft PR Comment, Is This Real In My Context).
2. **Visual Call Graph** — `react-flow` library (NOT D3). Reachability state color-coded: green=reachable, gray=dead, amber=via-config. Click node → jump to that finding. Mounted on Finding Detail page.
3. **Risk Heatmap of File Tree** — left-rail tree view colored by HIGH-density (count / file size). Tooltip shows top 3 rules. Click folder → filter findings table to that path. Tailwind heat scale from `bg-green-50` to `bg-red-700`.
4. **Vulnerability Timeline** — horizontal Gantt across last 30 runs. Each row = one rule_id; bar = first-seen → still-open / fixed. Plotly or pure SVG.

**Acceptance:**
- Playwright covers 4 new flows (1 spec file each, total +12 tests)
- Lighthouse score ≥ 95 on Finding Detail page
- Real-time chat latency p95 < 1.5s (cached Groq prompt)
- Zero new accessibility violations (axe-core)

**Drop-First (if Week A1 overruns):**
- Vulnerability Timeline → defer to Phase B Week 1
- Risk Heatmap polish (just ship MVP color scale)

**Resume bullet (A1):** *"Shipped an AI-chat-augmented finding review UI: streaming-LLM sidebar, interactive call-graph (react-flow), risk-heatmap file tree, vulnerability timeline. 12 new Playwright flows, Lighthouse 95+, zero accessibility regressions."*

---

### Week A2 — May 25–31: New Engines (Time-Travel + IaC)

**Goal:** Two engines no competitor combination ships together. Time-Travel is the thesis novelty; IaC is the competitive parity move.

**Tasks:**

1. **IaC Scanner** — wrap `checkov` (Terraform, CloudFormation, K8s, Dockerfile) + `kube-score` (K8s best-practice). Add adapter `CORE/adapters/iac_adapter.py`. Normalizer: ~40 new canonical IDs `IAC-*`. Migration 0013: `findings.iac_resource` + `iac_provider`. New samples in `TESTS/samples/iac-issues/`. **Drop:** GitHub Actions YAML scanning (Phase B).
2. **Time-Travel Vulnerability Analyzer** — new engine `CORE/engines/time_travel.py`. Walks last 50 commits using `git log --reverse`, runs lightweight diff-based analysis per commit (only files changed in commit), produces per-finding history: `first_seen_commit`, `first_seen_author`, `regression_count`, `near_fix_commits`. Migration 0014: `finding_history` table. New endpoint `GET /v1/runs/{rid}/findings/{fid}/history`. UI: timeline strip on Finding Detail.
3. **Engine docs:** `docs/engines/time_travel.md` + `docs/engines/iac_scanner.md` — algorithm, complexity bound, FP/FN known cases.

**Acceptance:**
- IaC: ≥ 50 tests added; smoke-tested against `iac-vulnerable-stacks` (public sample repo)
- Time-Travel: bounded to N=50 commits with `--full-history` opt-in (N=unbounded); time complexity documented; 30+ tests
- 0 CUSTOM-* in IaC output (canonical mapping complete)

**Drop-First:**
- `--full-history` mode (Phase B)
- Time-Travel author trust scoring (Phase B)

**Resume bullet (A2):** *"Designed and shipped Time-Travel Vulnerability Analysis — bounded-history static-analysis-over-git that surfaces when a vuln was introduced and which commits nearly fixed it. Plus IaC scanner covering Terraform/K8s/Dockerfile with 40+ canonical rule mappings and 50+ tests."*

---

### Week A3 — Jun 1–7: Heuristic Risk Predictor + Eval Expansion (Wave 1)

**Goal:** Add the explainable risk score; expand eval corpus by 8 repos (NOT 15 — 15 was over-scoped).

**Tasks:**

1. **Heuristic Risk Predictor** — new engine `CORE/engines/risk_predictor.py`. Per-file score 0–100 from documented weighted features: cyclomatic complexity (radon), churn (git log last 90d), age, author count, test-coverage gap, current HIGH-finding density. No ML — just a transparent weighted linear model with hand-calibrated weights from the 13-repo corpus. Migration 0015: `file_risk_scores` table. New endpoint `GET /v1/runs/{rid}/risk-map`. UI: integrate into Risk Heatmap from A1.
2. **Eval Wave 1 — +8 repos:**
   - **Tier 4 — Recent CVEs (4 repos):** pick 4 OSS Python/JS/Go projects with CVEs disclosed 2025–2026. Ground-truth YAML per repo.
   - **Tier 5 — Large frameworks (2 repos):** Flask trunk (already partially tested), django.nV expanded.
   - **Tier 7 — IaC (2 repos):** terraform-aws-vpc with known misconfigs, k8s-goat.
3. **Bench harness upgrade** — `scripts/run_benchmarks.sh` runs all 28 repos and produces `docs/evaluation/BENCHMARK_v5.md`. Time-budgeted: full run < 90 min.

**Acceptance:**
- Risk Predictor: 25+ tests; weight derivation documented in `docs/engines/risk_predictor.md`
- Eval: full 28-repo run completes in CI nightly job under 90 min
- Per-repo precision ≥ 95% on Tier 4–5 (HIGH only)

**Drop-First:**
- IaC tier (move to Phase B if Wave 1 takes longer than 3 days for the predictor)
- Bench harness CI integration (run locally only for now)

**Resume bullet (A3):** *"Built a transparent file-level risk predictor combining complexity, churn, age, author count, and coverage-gap into a 0–100 score; expanded evaluation corpus to 28 repos across 4 languages and 3 vulnerability tiers (recent CVEs, large frameworks, IaC); nightly benchmark CI completes in <90 minutes."*

---

### Week A4 — Jun 8–14: Eval Wave 2 + Security Hardening + Paper Draft

**Goal:** Eval bulletproofing pass 2 + ACR-QA-on-itself hardening + paper outline.

**Tasks:**

1. **Eval Wave 2:**
   - **Head-to-head vs Semgrep CE** (NOT Snyk — needs paid auth; Sonar — needs cloud quota): same 28 repos, side-by-side precision/recall/runtime. Output: `docs/evaluation/HEAD_TO_HEAD_SEMGREP.md`.
   - **5-rater peer study** (κ ≥ 0.78 target) — recruit 3 raters via KSIU faculty + 2 via LinkedIn. Run blind-rating on 30-finding sample.
   - **CVE recall battery:** expand from 10 → 20 CVEs. Document expected failure modes honestly.
2. **Security Hardening Pass on ACR-QA itself:**
   - Subprocess sandbox audit: every `subprocess.run` call in `CORE/` audited. Add `shell=False` enforcement test.
   - Secrets handling audit: every Groq key + JWT secret + DB password path checked. Add `bandit -ll` to pre-commit (currently medium-only).
   - Dependency confusion check: pin all internal-namespace packages explicitly.
   - **Dogfooding gate:** `acrqa scan .` against ACR-QA itself, quality gate must pass (0 HIGH). Wire into CI as required check.
3. **Paper draft:**
   - 8-page IEEE-style draft, **intro + related work + methodology + eval setup** complete (~4 of 8 pages).
   - LaTeX in `paper/`; bib in `paper/references.bib`.
   - Figures pulled from existing C4 diagrams + evaluation plots.

**Acceptance:**
- Head-to-head report shows ACR-QA's known advantages and known disadvantages honestly
- κ ≥ 0.78 from 5-rater study (or documented why not, with mitigation plan)
- ACR-QA self-scan: 0 HIGH findings on `main` branch
- Paper sections 1–3 (~4 pages) complete and reviewed by Dr. Samy

**Drop-First:**
- Paper sections 4–6 (defer to Week A6 polish or Phase B)
- 5-rater study → fall back to 3-rater if recruitment fails

**Resume bullet (A4):** *"Conducted head-to-head static-analysis benchmark vs Semgrep CE on 28 repos; designed and executed 5-rater blind agreement study (κ ≥ 0.78); hardened the platform via dogfooded quality gate and subprocess sandbox audit; published as part of 8-page IEEE-style thesis paper."*

---

### Week A5 — Jun 15–21: PR Risk Score + Launch MVP Plumbing (no public push)

**Goal:** Build the viral demo artifact (PR Risk Score) + lay infra for Phase B launch. **Zero public posts this week.**

**Tasks:**

1. **PR Risk Score** — new engine `CORE/engines/pr_risk.py`. Combines: HIGH finding count, reachability gate, exploit-verified count, taint-source-to-sink touches, file risk predictor average. Single 0–100 number per PR. Color: 0–30 green, 31–60 amber, 61–100 red. GitHub Action emits as PR check status. Migration 0016: `pr_risk_scores` table.
2. **Hosted SaaS infra (`acrqa.dev`):**
   - Domain registration (~$12)
   - Railway deploy of API + Postgres + Redis
   - Cloudflare proxy (free tier) for caching landing pages
   - Public read-only demo endpoint: `GET /v1/demo/dsvw` returns prerun DSVW findings
   - `acrqa.dev` landing page (port the existing `landing.html`)
3. **Per-user cost monitoring + quota** — required before opening signups:
   - `user_quota` table (migration 0017): tracks Groq token spend per user
   - Default daily quota: 100K tokens / user
   - Hard stop with friendly error when exceeded
   - Admin dashboard widget: total Groq spend trend
4. **Privacy + ToS docs** — `docs/PRIVACY.md` exists; add `docs/TERMS.md`. GDPR-style data deletion endpoint `DELETE /v1/users/me` (cascades to all user data).

**Acceptance:**
- PR Risk Score: GitHub Action posts comment with score + breakdown on every PR (tested on a dummy PR)
- `acrqa.dev/demo` returns DSVW findings JSON in <500ms (cached)
- Quota: synthetic 100K-token-spend test stops user gracefully
- Privacy docs reviewed by Ahmed

**Drop-First:**
- Cloudflare proxy (Railway has its own; only add if performance demands)
- PR Risk Score "breakdown" UI (just the number is enough for demo)

**Resume bullet (A5):** *"Designed PR Risk Score: single 0–100 mergeable-or-not signal combining reachability, taint coverage, exploit verification, and file risk into one CI check. Deployed read-only demo at acrqa.dev with per-user Groq-token quota and GDPR-compliant data deletion."*

---

### Week A6 — Jun 22–30: Defense Week (HARD CAP — no new code)

**Goal:** Defend. Nothing else.

**Tasks:**

1. **Defense deck — 25 slides:**
   - 1: Title
   - 2–4: Problem statement (alert fatigue, LLM hallucination, invisible test gaps)
   - 5–7: Architecture C4 (1 slide each: context, container, component)
   - 8–12: Pipeline walkthrough (Detection → Normalize → Reachability → AI → Quality Gate)
   - 13–16: Four outside-the-box features (Time-Travel, IaC, PR Risk, Heuristic Risk)
   - 17–19: Eval (28 repos, head-to-head vs Semgrep, 5-rater κ)
   - 20–22: Limitations honest list
   - 23–24: Future work (Phase B/C teaser)
   - 25: Q&A
2. **Q&A prep — 40 expected questions, written answers:**
   - "Why not just use Snyk?" (parity table)
   - "How honest is your recall?" (CVE recall section)
   - "Where does AI fail?" (hallucination + entropy + path feasibility)
   - "What's novel?" (Time-Travel + heuristic risk + RAG-grounded explanations)
   - Plus 36 more.
3. **Demo video — 5 min, 1920×1080:**
   - 0:00–0:30 — Hook (live scan, finding appears)
   - 0:30–2:00 — Dashboard walkthrough (Risk Heatmap → Finding Detail → AI Chat → Call Graph)
   - 2:00–3:30 — Time-Travel + IaC + PR Risk demo
   - 3:30–4:30 — Eval numbers + head-to-head
   - 4:30–5:00 — Sign-off + link to repo
   - Plus 90-sec teaser cut for X/LinkedIn (post-defense)
4. **Dry-run with Dr. Samy — by Jun 22 at the latest.**
5. **Final paper sections 4–8:** finish the IEEE draft, ready for Dr. Samy's signature.
6. **Tag v5.0.0** + sign + push to PyPI (after defense, not before).

**Acceptance:**
- Dr. Samy approves deck + paper draft
- Demo video uploaded to YouTube (unlisted initially)
- Defense passed

**Drop-First:**
- 90-sec teaser cut (post-defense fine)
- Paper sections 7–8 conclusion/future work (acceptable to defer)

**Resume bullet (A6):** *"Defended graduation thesis at KSIU on ACR-QA — automated code review platform with novel time-travel vulnerability analysis, heuristic risk prediction, and PR-merge risk scoring. Honest evaluation on 28-repo corpus; head-to-head with Semgrep CE; 5-rater inter-rater agreement κ ≥ 0.78."*

---

## 3. Phase B — Public Launch (Jul – Sep, 12 weeks)

### Exit criteria for Phase B

By Sep 30, 2026:
- ✅ v5.1.0 GA on PyPI
- ✅ Hosted SaaS at `acrqa.dev` with ≥ 100 active users (≥ 7-day retention)
- ✅ VSCode plugin published, ≥ 1,000 installs
- ✅ GitHub App installable, ≥ 50 organizations
- ✅ HN front-page or ProductHunt #5+ for the week
- ✅ ≥ 500 GitHub stars
- ✅ ≥ 5,000 PyPI downloads
- ✅ 0 P0/P1 user-reported security bugs unresolved

### Weekly themes (one per week, 1.8× pace)

| Wk | Theme | Killshot deliverable |
|---|---|---|
| B1 | Soft launch + telemetry | Sentry/PostHog wired; HN Show post; ProductHunt scheduled; r/Python + r/netsec posts |
| B2 | VSCode plugin | Inline squiggles + chat sidebar; published to Marketplace |
| B3 | GitHub App | Installable per-org; replaces the Action for serious users |
| B4 | Compliance reports | SOC2 + PCI-DSS + HIPAA + ISO 27001 (currently OWASP only); generated as Markdown + PDF |
| B5 | Auto-fix PR generator v2 | Actually opens PRs with the fix + reviewer summary |
| B6 | Cross-repo correlation | Same CVE flagged across user's repo portfolio |
| B7 | Live dependency risk heatmap | Author trust score; typosquat detection; OSV stream |
| B8 | Educational mode | CWE history + famous CVEs + "did you know" per finding; junior-dev audience |
| B9 | Public benchmark page | `acrqa.dev/benchmarks` — interactive comparison vs Semgrep, updated nightly via CI |
| B10 | Performance scaling | 1M LOC repo in <5 min; parallel adapter execution; result streaming |
| B11 | External security audit | Pay $1500 or trade for thesis exposure; one independent pen-test report |
| B12 | v5.1.0 GA + retrospective | Tag, blog post, retrospective doc; thank-you email to all users |

### Phase B exit-or-iterate decision (Sep 30)

If exit criteria not met by Sep 30, **do not extend Phase B**. Cut features, ship what's working, move to Phase C with honest postmortem. Time-boxing protects against scope inflation.

---

## 4. Phase C — Compound (Oct 2026 – Mar 2027, 24 weeks)

Optional, conditional on Phase B traction. Themes (monthly):

| Month | Theme |
|---|---|
| Oct | Paper submission to ICSE/FSE/USENIX/MSR workshop (or arXiv preprint) |
| Nov | Conference talk submission: PyCon, BSides Riyadh, DEF CON workshop |
| Dec | Fine-tune a small CodeLlama variant on our 66-rule KB (research contribution) — only if usage data shows demand |
| Jan | Enterprise features: SSO/SAML, audit log, on-prem image, RBAC depth → optional commercial track |
| Feb | OSS community: Discord, monthly office hours, contributor docs; 500-member target |
| Mar | v6.0.0 release; year-1 retrospective post; PhD application support if relevant |

Phase C tasks are illustrative, not committed. Re-plan in early October after Phase B exit retrospective.

---

## 5. The Four Outside-the-Box Bets — Re-Justified

Picked from 8 candidates after rethink. Each must be: **measurable, defensible, ships in Phase A.**

| Bet | Why it ships in A | Thesis claim | Resume claim |
|---|---|---|---|
| **Time-Travel Vuln Analysis** | Bounded to last 50 commits; uses existing engines per-commit; complexity is documented O(N × scan_time) | "Cross-commit static-analysis-over-git as a first-class signal" | Novel feature in the platform |
| **IaC Scanner** | Wraps mature OSS tools (checkov, kube-score); 1-week wrap job | "Competitive parity with Snyk/SonarQube IaC capabilities" | Coverage expansion to infra |
| **PR Risk Score** | Combines existing signals into a single number; viral demo artifact | "Decision-grade output for non-security reviewers" | UX innovation |
| **Heuristic Risk Predictor** | NOT ML — transparent weighted linear model; defensible | "Explainable risk surface ahead of detection; auditable weights" | Engineering for honesty over hype |

**Explicitly rejected:**
- Adversarial LLM Code Scanner — no ground truth, can't evaluate, bad thesis bet.
- Predictive Risk ML — 13 repos is not training data; would overfit to nothing.
- Code Provenance Graph — vague; no clear user pain solved.

---

## 6. Testing — Beyond Perfect

Current baseline (v4.6.0): 2,279 Python + 66 TS = 2,345 tests · 84.89% coverage · κ = 0.74 (2 raters) · 13 repos · CVE recall 20% (2/10).

| Layer | Today | End Phase A | End Phase B |
|---|---|---|---|
| Python unit/integration tests | 2,279 | **2,900** | 3,500 |
| TypeScript tests | 66 | 120 | 180 |
| Coverage | 84.89% | **88%** | 92% |
| Mutation score (`CORE/engines/` only) | not measured | **65%** | 80% |
| Eval repos | 13 | **28** | 40 |
| CVE recall | 20% (2/10) | **40% (8/20) — documented failure modes** | 50% |
| Inter-rater κ | 0.74 (2 raters) | **0.78 (5 raters)** | 0.82 (10 raters) |
| Visual regression | none | **All UI routes (Playwright screenshots)** | All UI + i18n variants |
| Soak test | none | **24 hr** | 7 day |
| Head-to-head vs competitors | 0 | **1 (Semgrep CE)** | 3 (+ SonarQube + Snyk) |
| Dogfooded self-scan | manual | **CI required check** | CI required + drift alerts |
| Fuzz testing | partial (hypothesis) | **All normalizer inputs** | All endpoints |

### Test corpus expansion strategy

Eval growth must be **quality over quantity**: every new repo gets a ground-truth YAML in `TESTS/evaluation/ground_truth/`. A repo without ground truth is a smoke test, not eval data. Track separately.

- **Tier 1 — CVE recall (target 20):** real CVEs from disclosed advisories, one HIGH finding per CVE.
- **Tier 2 — Curated benchmarks:** DVPWA, Pygoat, VulPy, DSVW, NodeGoat, WebGoat, k8s-goat. Existing.
- **Tier 3 — Polyglot:** Python+JS+Go projects to exercise cross-language correlator.
- **Tier 4 — Recent CVEs (2025–2026):** added in Phase A.
- **Tier 5 — Large frameworks:** Flask, Django, FastAPI, Express — primarily for FP rate.
- **Tier 6 — IaC:** Terraform, K8s, Dockerfile samples.
- **Tier 7 — Self-eval:** ACR-QA on ACR-QA. Required CI check.

---

## 7. Security Hardening (Continuous, Not One-Week)

ACR-QA executes untrusted code via subprocess and consumes user-provided LLM outputs. A serious tool gets serious about its own attack surface. Tracked as a continuous track, not a sprint.

| Area | Pass cadence | Owner |
|---|---|---|
| Subprocess sandbox audit | Quarterly + before every release | engineering |
| Secrets handling review | Before every release | engineering |
| Dependency confusion / typosquat self-check | Monthly via `pip-audit` + `safety` | CI |
| LLM prompt-injection defense (in user code → ACR-QA's chat) | Phase B Week 4 hardening | engineering |
| External pen-test | Phase B Week 11 | external |
| Dogfooded self-scan quality gate | Every commit | CI |

**Bandit + Semgrep run on ACR-QA's own source as part of pre-commit.** Currently runs on user repos only; this gap is closed in Phase A Week 4.

---

## 8. Privacy + Data Governance (Hosted SaaS Track)

Opening signups means becoming a data controller under GDPR/equivalents. Required before A6 (defense — Dr. Samy will ask):

- ✅ `docs/PRIVACY.md` updated (existing — needs hosted-SaaS update in A5)
- ✅ `docs/TERMS.md` written (new, A5)
- ✅ `DELETE /v1/users/me` cascade endpoint with confirmation email (A5)
- ✅ Data retention policy: scan results purged after 90 days unless user pins (A5)
- ✅ Cookie consent banner on `acrqa.dev` (B1)
- ✅ Per-region data residency: EU users → EU region (B6 — only if EU users sign up)
- ✅ Right-to-export endpoint: `GET /v1/users/me/export` returns ZIP of user data (B4)

---

## 9. Risks + Mitigations (Re-thought)

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Defense slips because of feature creep | High | Catastrophic | **Week A6 hard cap.** No new code. Drop-First lists enforced. |
| Burnout from 12-hr-day pace | Med-High | High | Sunday off non-negotiable. Track sleep + push back if it slips. |
| Hosted SaaS infra costs balloon | Low | Medium | Free tiers + hard quota; per-user 100K Groq tokens/day; kill switch on Railway free-tier limits. |
| Soft launch flops on HN | Medium | Medium | Have two angles: feature-driven and thesis-story-driven. Re-post under second angle if first dies in <24h. |
| New engines (Time-Travel) too slow on real repos | Medium | High | Bounded to N=50 commits by default; `--full-history` opt-in. |
| Groq free-tier rate limit hit at launch | Medium | High | Key rotation already implemented (4-key pool); add Ollama fallback documented; quota system in A5. |
| External rater recruitment fails | Medium | Medium | Fall back from 5 to 3 raters; document attempt. |
| Adversarial users abuse hosted SaaS | High | Medium-High | Per-IP rate limit; abuse@ contact; honeypot reCAPTCHA on signup; Cloudflare WAF if needed. |
| PyPI credentials compromise | Low | Catastrophic | OIDC trusted publishing (already implemented); no static credentials. |
| Defense panel asks a question I haven't prepared | Medium | High | 40-question Q&A prep doc; rehearse dry-run with Dr. Samy before A6. |

---

## 10. What's Explicitly Dropped (vs Phase A v2 draft)

- ❌ Mobile-responsive UI pass — code review is not a phone task
- ❌ Internationalization to 6 languages — EN/AR is enough proof; more is dead weight
- ❌ 3 themes (light + high-contrast AAA) — dark mode is enough
- ❌ Onboarding wizard in Phase A — too rich; slips to Phase B
- ❌ D3.js custom call-graph — `react-flow` saves 2 days
- ❌ Adversarial LLM Code Scanner — no ground truth
- ❌ Predictive Risk **ML** — 13 repos isn't training data (replaced by heuristic predictor)
- ❌ Code Provenance Graph — vague
- ❌ HN/ProductHunt launch during defense week — two crises at once
- ❌ Snyk + Sonar head-to-head in Phase A — paid auth + quota issues (Phase B instead)
- ❌ 15 new eval repos in one week — 8 with quality ground truth beats 15 without

---

## 11. Success Metrics by Phase

| Metric | Today | End A | End B | End C |
|---|---|---|---|---|
| ACR-QA version | v4.6.0 | v5.0.0 | v5.1.0 | v6.0.0 |
| Tests (Py + TS) | 2,345 | 3,020 | 3,680 | 4,500 |
| Coverage | 84.89% | 88% | 92% | 93% |
| Eval repos | 13 | 28 | 40 | 60 |
| CVE recall | 20% | 40% | 50% | 60% |
| Inter-rater κ | 0.74 | 0.78 | 0.82 | 0.85 |
| GitHub stars | (~unknown) | 100 (organic) | 500+ | 2,000+ |
| PyPI downloads / mo | 0 | 100 (defense-week spike) | 5,000 | 25,000 |
| Active users | 0 | 0 (no public push) | 100 | 1,000 |
| API endpoints | 37 | 45 | 60 | 75 |
| Languages supported | Py + JS/TS + Go | + IaC | + Java + Rust (if demand) | + |
| Migrations | 11 | 17 | 25 | 35 |
| Conf talks / papers | 0 | 1 (paper draft) | 1 (submitted) | 2 (talk + accepted paper) |

---

## 12. Daily + Weekly Rituals

### Daily
- Morning: 10-min plan (today's top 3 tasks from this doc's Drop-First-aware queue)
- Evening: commit + push (CLAUDE.md pre-commit checklist enforced)
- Log: 1-line entry in `docs/PHASE_A_LOG.md` ("what shipped today, what's blocked")

### Weekly (Sunday off)
- Saturday end-of-day: 30-min retro — what slipped, what to drop next week
- Update §13 progress snapshot
- Push memory updates if anything novel emerged (gotchas, decisions, feedback)

### Phase boundaries
- End of Phase A: write `docs/PHASE_A_RETRO.md`. What I'd do differently. Hand to Phase B.
- End of Phase B: same. Plus public retrospective blog post.

---

## 13. Progress Snapshot

**As of May 19, 2026:**

- Phase A Week 1 (UI Killshot): **5/5 shipped ✅ COMPLETE**
- Phase A Week 2 (New Engines): **2/2 shipped ✅ COMPLETE**
  - ✅ A2.1–3 IaC Scanner — `CORE/engines/iac_scanner.py`, 28 canonical rules,
    migration 0013 (`iac_provider` + `iac_resource`), `POST /v1/scans/iac`,
    sample fixtures in `TESTS/samples/iac-issues/`, 52 + 6 = 58 backend tests.
  - ✅ A2.4–5 Time-Travel Analyzer — `CORE/engines/time_travel.py`,
    migration 0014 (`finding_history` cache table), `GET /v1/findings/{fid}/history`,
    `FindingHistory.tsx` React component wired into FindingModal as History tab,
    23 + 4 backend tests + 7 Vitest tests.
- Backend tests: 2,279 → **2,405** (+126 across A1 + A2)
- Frontend tests: 66 → **104** (+38 across A1 + A2)
- Grand total: **2,509**
- Engine docs: `docs/engines/iac_scanner.md`, `docs/engines/time_travel.md`
- Defense date: **placeholder Jun 25, awaiting Dr. Samy confirmation**
- v5.0.0 target tag: **Jun 28, 2026** (post-defense)
- Next: Phase A Week 3 — Heuristic Risk Predictor + Eval Wave 1 (+8 repos with
  ground-truth YAMLs)

Update this section after every commit affecting Phase A scope. Don't duplicate the per-week tables — just track top-of-mind state.

### Open questions for Ahmed (resolve in Week A1)

1. Defense date confirmation from Dr. Samy
2. Domain `acrqa.dev` — already owned? (If not, register early A1)
3. Budget: external pen-test (~$1500) acceptable in Phase B Week 11?
4. Are KSIU faculty raters reachable for the 5-rater study?

### Invocation pattern (recap from v2)

- `where are we` → read §13 + report top-of-mind state + next 3 tasks
- `go god mode phase A` → execute all unchecked tasks in Phase A
- `go god mode A.N` → execute Week N tasks in Phase A
- `go god mode` (no args) → resume the highest-priority unfinished week

---

*Plan v3 supersedes v2 (which is complete). Update this doc at the end of each week — do not let it rot.*
