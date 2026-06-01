# ACR-QA God Mode Plan v5 — From Thesis to Best-in-University

> **Created:** 2026-05-31
> **Horizon:** ~25 weeks (defense day is just one waypoint, not the finish line)
> **Goal:** Best thesis project at KSIU + backend/DevOps portfolio flex + real product with users + publishable academic artifact
> **Author:** Ahmed Mahmoud Abbas (KSIU, supervised by Dr. Samy AbdelNabi)

---

## 0. Vision

ACR-QA v5.0.0rc1 is already committee-best material on numbers alone (P4 Confirmed Tier 96.4% conservative / 100% optimistic precision, F1=98.2%, 100% CVE recall, 2,757 tests, 12 contributions, X1–X5 empirical battery). The next 25 weeks are about **converting that engineering work into four kinds of outcomes**:

1. **Academic legitimacy** — a citable artifact, peer-reviewed paper, formal replication package
2. **Engineering credibility** — a portfolio piece that makes any senior backend/DevOps hiring manager say "I want to talk to this person"
3. **Real-world adoption** — users, GitHub stars, deployments, CVE filings — proof the work matters outside the thesis room
4. **Defense day victory** — a memorable performance, not just a passing one

This document is the master plan. Every section can be picked up independently — we don't need to do everything, but each lane multiplies the others.

---

## 0.5 Cost Legend

Every item below is tagged with a budget marker so a fresh-grad student can plan realistically:

| Marker | Meaning | Examples |
|--------|---------|----------|
| 🆓 | Fully free | OSS tools, GitHub Actions, Sigstore, Discord, Hacker News post |
| 💵 | Small one-time or low recurring ($0–$50 total) | Domain name (~$10/yr), Chrome Web Store fee ($5 once), JetBrains marketplace ($) |
| 💰 | Meaningful cost ($50+ or ongoing) | Bug bounty payouts, paid a11y audit session, IEEE conference registration |
| 🎓 | Free with student / OSS discount available | Many cloud free tiers, GitHub Student Pack, conference student rates |

**Default to free.** Every paid item below has a free-or-cheap alternative noted.

---

## 1. Strategic Lanes — Index

| # | Lane | What it proves | When |
|---|------|----------------|------|
| **2** | Defense Day Stagecraft | "Best presentation in the room" | Weeks 1–4 |
| **3** | Backend Showoff Layer | "Production-grade engineer" | Weeks 2–10 |
| **4** | DevOps / Platform Layer | "SRE/platform mastery" | Weeks 3–12 |
| **5** | Academic Rigor | "Publishable research" | Weeks 1–8 |
| **6** | External Validation & Story | "This work matters in the wild" | Weeks 4–14 |
| **7** | Product / Business Layer | "Founder/PM thinking" | Weeks 8–18 |
| **8** | OSS Community Building | "Open-source maintainer" | Weeks 6–25 |
| **9** | Engineering Depth | "Reviewer-defeating rigor" | Weeks 4–16 |
| **10** | Security / Compliance Flex | "Enterprise-ready" | Weeks 10–20 |
| **11** | Frontier / Publishable Ideas | "Research lead" | Weeks 12–25 |
| **12** | Outside-the-Box Wild Cards | "Memorable" | Anywhere |

---

## 2. Defense Day Stagecraft

Defense day is one 45-minute slot. The technical content is locked. The remaining lever is *theatrics* — how the work lands in a committee's memory.

### 2.1 Live Scan During Defense
- **Setup:** Open the dashboard. Examiner volunteers a public GitHub URL. Paste it. Scan completes in ~2 minutes. Confirmed Tier findings appear live.
- **Risk mitigation:** Pre-cached scans on 5 popular repos (Django, FastAPI, Flask, axios, gin) as fallback if the wifi dies or examiner-chosen repo is too large.
- **Why it works:** Every committee has seen 50 PowerPoints. They've seen 0 live security demos.

### 2.2 Live Exploit Demo (X2 in Action)
- **Setup:** Pre-built Docker sandbox with SQLi vulnerable app. Trigger ACR-QA scan → finding detected → exploit_verifier runs in a sandboxed container → SQL rows appear on screen → patch applied → exploit fails.
- **60 seconds** end to end. Pre-rehearsed.
- **Bonus:** Run the same demo against command injection and SSTI as a tab carousel.

### 2.3 Three-Way Bake-Off Split Screen
- **Setup:** Three terminals side-by-side: Bandit, Semgrep, ACR-QA. Scan the same fresh repo (cached for speed). Show results side-by-side, then show CVE coverage: 1/8 vs 5/8 vs 8/8.
- **Slide:** the head-to-head F1 table from §5.16 of the thesis.

### 2.4 "1,942 → 55" Funnel Reveal Slide
- **Animation:** five stacked horizontal bars, each one shrinking and labelling its filter (Raw → H/M sev → Reachability → Security-tier → P3 taint → P4 Confirmed). Counter-animation on the right shows precision climbing (8.6% → 26.9% → 96.4%) and recall holding at 100%.
- **The single most memorable slide in the deck.** It's the entire thesis in 5 seconds.

### 2.5 Backup Video for Every Live Demo
- **Reality check:** Live demos fail. Wifi fails. Docker doesn't start. The screen disconnects.
- **Plan:** Record OBS video of every live segment. If anything breaks mid-demo, click the video file and narrate over it. Committee won't notice.

### 2.6 Q&A Card Deck
- 40 pre-rehearsed Q&A cards (already in `docs/DEFENSE_QA.md`). Print physical index cards. Bring them.
- For each card: ≤30-second verbal answer + reference to the exact thesis section.

### 2.7 The Opening 90 Seconds
- This is the only minute the committee is fresh. Burn it well.
- **Suggested opening:** "Three numbers. 96.4% precision. 100% CVE recall. F1 98.2%. No open-source SAST tool achieves this trio. Here's how." Then go straight to the funnel slide.

---

## 3. Backend Showoff Layer

The technical layer that makes a senior backend engineer go *"wait, you built that as an undergrad?"*

### 3.1 Public Hosted Demo (`acrqa.<domain>`) 💵🎓
- **What:** Anyone visits the URL, pastes a public GitHub repo, gets a real scan report.
- **Stack:** Railway / Fly.io (already configured), Cloudflare in front, rate-limited at 5 scans/IP/hour.
- **Cost:** Domain ~$10/yr (Namecheap / Cloudflare Registrar). Railway has $5/mo free credit with GitHub Student Pack 🎓. Cloudflare free tier covers everything you need. **Total: ~$10/yr.**
- **Free-est alternative:** Use a `.dev` subdomain you already own, or skip custom domain and use the default Railway URL ($0).
- **Why first:** It's the foundation for every other "external proof" move. HN, Twitter, peer review — all need a URL.
- **Effort:** 1 week (most infra exists; needs auth-less demo path, abuse protection, and a homepage).

### 3.2 GitHub Webhook Receiver 🆓
- **What:** A GitHub App that, when a PR opens, autoscans the diff and posts a PR comment with Confirmed-Tier findings.
- **Why:** This is the "real workflow" demo. Examiners and HN readers will all want this exact feature.
- **Effort:** 1–2 weeks (webhook handler + app manifest + diff-scoped scan path + PR-comment renderer).

### 3.3 Published Client SDKs 🆓
- **What:** `pip install acrqa-client`, `npm install @acrqa/client`. Generated from your OpenAPI spec via `openapi-generator`.
- **Bonus:** Go and Rust clients.
- **Why:** Shows you understand client/server boundary, polyglot ecosystems, semver, and packaging.

### 3.4 GraphQL Endpoint Over REST 🆓
- **What:** Add `/graphql` mounted on the existing FastAPI app via Strawberry. Resolve to the same DB layer the REST endpoints use.
- **Why:** Knowing when *not* to use GraphQL is the senior signal. Document the trade-off in `docs/architecture/GRAPHQL.md`.

### 3.5 Plugin System (External Rule Packs) 🆓
- **What:** `pyproject.toml` `entry_points` for `acrqa.rules`. Anyone can `pip install acrqa-rule-pack-foo` and add custom rules.
- **Why:** Shows extensibility design. Now ACR-QA isn't just your tool — it's a platform others can build on.

### 3.6 Multi-Tenancy 🆓
- **What:** Orgs, RBAC (owner/admin/member/viewer), per-org scan budgets, per-org API keys, per-org dashboards.
- **Why:** Production-grade auth model. This is the single biggest gap between "demo" and "product."

### 3.7 WebSocket Live Progress (Beyond SSE) 🆓
- **What:** Bidirectional channel for scan progress + interactive "ask the AI explainer a follow-up" pattern.
- **Why:** SSE is already there. WebSockets show you understand when each is appropriate.

### 3.8 gRPC Sidecar Mode
- **What:** Expose the analysis pipeline as a gRPC service for downstream tools to consume.
- **Why:** "I know REST. I know GraphQL. I know gRPC. Here's when each is right." That's the trifecta on any backend resume.

### 3.9 Event-Sourced Scan History
- **What:** Each scan emits domain events to an append-only log. Any past scan can be replayed from events.
- **Why:** This is event sourcing on a real domain. Architecture-interview gold.

### 3.10 CQRS Split
- **What:** Separate write-side (scan submission) from read-side (finding queries). Reads served from a materialised projection (Postgres logical replication target or Redis).
- **Why:** Same as above — patterns named in every architecture book, rarely seen in undergrad work.

---

## 4. DevOps / Platform Layer

The infrastructure layer that makes an SRE / platform engineer take notice.

### 4.1 Cosign + SLSA Level 3 + Sigstore Rekor 🆓
- **What:** Sign container images and release artifacts with Cosign. GitHub Actions provenance attestation at SLSA Level 3. Every scan attestation logged to Sigstore Rekor transparency log.
- **Why:** This is *exactly* the supply-chain story the security industry is asking for in 2026. You'd be ahead of most commercial vendors.

### 4.2 Helm Chart on ArtifactHub + Terraform Module on Registry 🆓
- **What:** Publish the existing Helm chart to ArtifactHub. Publish the existing Terraform module to the Terraform Registry.
- **Why:** "I shipped infrastructure that other people can consume" is a senior platform signal.

### 4.3 Live SLO Dashboard 🆓
- **What:** Public Grafana page showing current SLO burn rate (availability, p95 latency, scan completion, AI latency). Always-on, always-public.
- **Cost:** Grafana Cloud free tier (10k series, 50GB logs/mo) is enough. Or self-host Grafana — free.
- **Why:** SLO/SLI thinking on a real service is rare even at staff-engineer level.

### 4.4 k6 Continuous Load Test 🆓
- **What:** Scheduled k6 run hitting the hosted demo at 1000 RPS for 10 min, results posted to a public dashboard nightly.
- **Cost:** k6 OSS is free. (k6 Cloud is paid — don't use it.) GitHub Actions free minutes cover the cron runs.
- **Why:** Proves performance claims continuously, not as a one-time evaluation result.

### 4.5 Chaos Engineering 🆓
- **What:** Toxiproxy in front of Postgres and Redis. Litmus or Chaos Mesh on the K8s cluster.
- **Demo scenarios:** kill Celery worker mid-scan, throttle Postgres connections, blackhole Groq API. Show graceful degradation.
- **Why:** Most undergrad systems break the moment anything goes wrong. Showing resilience tests = senior thinking.

### 4.6 KEDA Autoscaling on Celery Queue Depth 🆓
- **What:** Celery queue length drives pod replica count. One slide showing pods spawn under load = killer DevOps proof.

### 4.7 Distributed Tracing End-to-End 🆓
- **What:** OpenTelemetry spans for every stage of the 12-stage pipeline. Jaeger UI showing the trace tree for a single scan.
- **Why:** Most apps don't trace. This is observability done right.

### 4.8 Kubernetes Operator
- **What:** A custom resource definition `ScanJob` and an operator that reconciles desired vs actual state.
- **Why:** Operators are CRD-level Kubernetes mastery. This is staff-engineer territory.

### 4.9 OPA Gatekeeper Quality-Gate Integration
- **What:** Express the quality gate as Rego policies in OPA. ACR-QA emits findings → OPA decides pass/fail.
- **Why:** Externalising policy = production maturity.

### 4.10 Service Mesh + Vault PKI for mTLS
- **What:** Linkerd or Istio between services. HashiCorp Vault issues short-lived mTLS certs.
- **Why:** Zero-trust networking + secret rotation — both senior platform concerns.

### 4.11 Production Cost Dashboard 🆓
- **What:** Live page: "$X per 1,000 scans, broken down by Groq API + compute + storage." Shows you think about FinOps.
- **Cost:** The dashboard itself is free. The cloud costs it tracks are whatever the hosted demo (§3.1) accrues.

### 4.12 GitOps via ArgoCD 🆓
- **What:** All deploys flow from a `deploy/` repo. ArgoCD reconciles cluster state. Audit log of every deploy.

### 4.13 PostgreSQL HA + PITR
- **What:** Streaming replication primary→replica, WAL archiving for point-in-time recovery. Demo the restore.

### 4.14 Cloud KMS-Backed ECDSA Signing
- **What:** Move the ECDSA-P256 signing key from local file to AWS KMS / GCP Cloud KMS. Signature still verifies; key never leaves the HSM.

---

## 5. Academic Rigor

The work that turns "good thesis" into "publishable research."

### 5.1 Five-Rater Inter-Rater Reliability Study (κ ≥ 0.78) 🆓
- **What:** Recruit 5 KSIU faculty / senior students. Each independently labels the same 50-finding sample as TP/FP/NR. Compute Fleiss' κ.
- **Why:** This is the *only* claim in the thesis still marked "in progress." Finishing it closes the last evaluation gap.
- **Effort:** 1 week recruitment + 1 week labelling + 1 day analysis = ~2.5 weeks.

### 5.2 Zenodo Replication Package with DOI 🆓
- **What:** Upload corpus pins, triage labels, scripts, ground-truth YAMLs, and aggregated results to Zenodo. Get a DOI.
- **Why:** Now your thesis is a *citable* artifact. Anyone, ever, can reproduce your numbers.

### 5.3 OSF Pre-Registration 🆓
- **What:** Pre-register the X1, X3, X4 methodologies on Open Science Framework *before* re-running them. Lock in the analysis plan.
- **Why:** Committee can't accuse cherry-picking when the methodology is timestamped publicly.

### 5.4 Venue Submission 💰🎓
- **Targets (by fit + timeline):**
  - **OWASP AppSec Days** (regional, lower bar, fast turnaround) — submission deadline 2026-Q3. Submission 🆓; registration usually 🆓 for speakers.
  - **IEEE SecDev** — industry-academic. Submission 🆓; registration ~$200 student rate 🎓.
  - **MSR (Mining Software Repositories)** — X4 backtest fits perfectly. Submission 🆓; registration ~$300 student rate 🎓.
  - **ICSE SEIP track** — submission 🆓; registration ~$400 student rate 🎓 — biggest venue, biggest cost.
- **Cost reality:** **Submission is always free.** Only registration (if accepted) costs money. Most have student rates, scholarships, or virtual-only options.
- **Free move:** Submit to a free venue + a paid venue. If only the paid one accepts, decide then. "Submitted to" line is what matters academically.
- **Why:** A "Submitted to ICSE" line on the thesis title page changes the conversation entirely.

### 5.5 Convert Chapter 5 to a Stand-Alone Paper 🆓
- **What:** Take §5.10–§5.17 (adversarial + Confirmed Tier + head-to-head + X1–X4) and shape it into an 8-page paper.
- **Why:** Maximum re-use of work already done. Could be your first publication.

### 5.6 Formal Specification of Dedup Function
- **What:** Express the CanonicalFinding dedup invariants in TLA+ or Alloy. Show that no two findings with the same fingerprint can survive dedup.
- **Why:** Formal methods on a real product = serious academic flex.

### 5.7 Property-Based Testing with Hypothesis 🆓
- **What:** For each canonical rule, define property: "if input is valid Python with pattern P, finding F is emitted." Test thousands of generated inputs.
- **Why:** Stronger than example-based testing. Shows you understand testing as exploration.

### 5.8 Replication Across Independent Hardware 🆓
- **What:** Run the full benchmark on 3 different machines (your laptop, a Railway container, a cloud VM). Show numbers match.
- **Why:** Reproducibility evidence beyond "trust me."

---

## 6. External Validation & Story

The non-technical work that translates engineering into recognition.

### 6.1 Hacker News Post 🆓
- **Timing:** The day after defense, when you can say "presented at KSIU yesterday."
- **Headline angle (test 3 variants):**
  - "I combined 19 SAST tools and got 96.4% precision with 100% CVE recall"
  - "Show HN: I scanned 400 LLM-generated code samples — they have 8× more vulnerabilities than humans"
  - "Show HN: Open-source SAST that beats Bandit (F1 22%) and Semgrep (45%) at F1 98%"
- **Bring receipts:** Public demo URL + GitHub repo + thesis PDF in the post.

### 6.2 Twitter/X Thread 🆓
- 10-tweet thread with the X2 exploit GIFs, the funnel diagram, the head-to-head table, the AI-code finding.
- Tag: `@semgrep`, `@PyCQA`, `@anthropicai`.

### 6.3 Blog Series 🆓
- **Post 1:** "How I beat Semgrep at F1 by combining 19 tools" (technical)
- **Post 2:** "RAG + entropy filtering: how to make LLM code review trustworthy" (AI-focused)
- **Post 3:** "AI-generated code introduces 8–12× more vulns than humans. I measured it." (viral hook from X3)
- **Post 4:** "How I time-traveled through Django's git history to predict CVEs" (X4)

### 6.4 Demo Video on YouTube 🆓
- 5-min walkthrough using `docs/DEMO_VIDEO_SCRIPT.md`.
- Subtitles in EN + AR (showcases the i18n work).

### 6.5 Conference Talk Submissions 🆓
- **OWASP local chapters** — easy to land, gives you a track record.
- **DEF CON AppSec Village** (long shot, but submission costs nothing).
- **University TEDx** — KSIU TEDx if one exists. Story format.

### 6.6 LinkedIn Article + Resume Section 🆓
- **Section:** "Thesis project: ACR-QA — 96.4% precision SAST orchestrator with public demo at ..."
- **Article:** 3-paragraph LinkedIn post linking back to the blog series.

### 6.7 Cold Outreach to Practitioners 🆓
- DM 20 practitioners (security engineers at companies you'd like to work at) asking for 15 minutes of feedback.
- Half will ignore. The other half become your portfolio reviewers. Some hire.

---

## 7. Product / Business Layer

The lens that turns "open source tool" into "real product." Even if you never charge a dollar, building this proves PM/founder thinking.

### 7.1 ICP & Persona Docs 🆓
- **Document:** `docs/product/PERSONAS.md` — three personas: solo developer, security engineer at a 50-person startup, AppSec lead at a 500-person company.
- **Why:** Shows you think about *who* the tool is for, not just what it does.

### 7.2 Pricing Model on Paper 🆓
- **Doc:** `docs/product/PRICING.md` — Free (self-hosted forever), Pro ($X/mo hosted with multi-tenancy), Enterprise (SSO, audit log, SLA).
- **Why:** Even un-implemented pricing tiers communicate business maturity.

### 7.3 Roadmap Public Page 🆓
- **What:** A live `roadmap.md` or GitHub Projects board with "Now / Next / Later" lanes, prioritised.
- **Why:** Open roadmaps are a strong product signal.

### 7.4 Telemetry & Analytics 🆓
- **What:** Opt-in anonymous usage metrics (PostHog or Plausible). Track which features are actually used.
- **Cost:** PostHog Cloud free tier (1M events/mo). Plausible has a self-hosted option for $0. Or just stick with PostgreSQL + a simple events table.
- **Why:** "I make data-driven decisions" — proves it with a public dashboard.

### 7.5 Onboarding Flow Audit 🆓
- **What:** Walk a new user through the first scan. Time it. Friction-log every step. Then close the top 3 frictions.
- **Why:** UX work that's measurable.

### 7.6 Case Study Page 🆓
- **What:** "Customer success" page on the marketing site — but with *real* deployments. Even 3 small users (a friend's side project, a university lab, an open-source repo) count.

### 7.7 Status Page (status.acrqa.dev) 🆓
- **What:** Public StatusPage or Cachet showing service uptime in real time.
- **Cost:** Better Stack free tier (10 monitors). Or self-host Cachet/Statping. Don't use Atlassian Statuspage — it's expensive.

---

## 8. OSS Community Building

Turning the repo into a real open-source project.

### 8.1 Governance & Policy Docs
- `GOVERNANCE.md` — how decisions get made.
- `CODE_OF_CONDUCT.md` — Contributor Covenant 2.1.
- `CONTRIBUTING.md` — already exists; tighten it.
- `SECURITY.md` — disclosure policy with PGP key.
- `MAINTAINERS.md` — who's responsible for what.

### 8.2 Issue & PR Templates
- Bug report template
- Feature request template
- Rule contribution template (for the plugin system)
- PR template with checklist

### 8.3 Discussions Enabled
- GitHub Discussions for Q&A, ideas, show-and-tell.
- Pin a "weekly office hours" thread.

### 8.4 Discord / Slack Community
- Discord server with channels: #general, #help, #rule-pack-dev, #show-and-tell, #release-notes.

### 8.5 Release Cadence
- Monthly point releases. Quarterly minor releases. Pre-announced changelog drafts in Discussions.

### 8.6 Bug Bounty Program 💰
- Public scope: the hosted demo + the released binary.
- HackerOne Bug Bounty Triage or self-hosted via GitHub Security Advisories.
- **Cost:** Pay $50–500 per accepted finding. If you accept 3 findings = $150–$1,500 out of pocket.
- **🆓 alternative — "Acknowledgement-only" program:** publish a "Hall of Fame" page that names researchers who report findings. No cash, just credit. Resume-worthy for them. Most thesis-grade projects use this model.
- **Skip if** you don't have the budget — move to acknowledgement-only.

### 8.7 Hacktoberfest Participation 💵
- Tag 30 issues `good-first-issue`. **Participating** is free 🆓; **sponsoring t-shirts** costs ~$100–200 if you want to send swag.
- **Recommendation:** Just opt in for free — DigitalOcean / Hacktoberfest sends shirts to contributors directly. You don't pay anything.

### 8.8 Sponsors Page 🆓
- GitHub Sponsors + Open Collective.
- Even $10/mo from 5 people = real validation. **You earn money here, don't spend it.**

---

## 9. Engineering Depth

The work that makes a senior reviewer say "this is unusually thorough."

### 9.1 Mutation Testing 🆓
- **What:** `mutmut` on the CORE engines. Target ≥75% mutation score.
- **Why:** Coverage % is a tripwire (already at 84.89%); mutation score is the real metric.

### 9.2 Fuzz Testing 🆓
- **What:** Atheris or hypothesis-fuzz on the tool runner subprocess interface and the normaliser.
- **Why:** SAST tools should themselves be hardened against malicious input.

### 9.3 Continuous Benchmark Suite 🆓
- **What:** Nightly run of the full ablation + bootstrap + CVE recall on a `benchmarks` branch. Results posted to a Grafana dashboard. Regressions alert.
- **Why:** Performance claims that aren't continuously verified rot.

### 9.4 Bundle Size & Lighthouse Budget 🆓
- **Dashboard:** Enforce JS bundle <300KB gzipped. Lighthouse Performance ≥90.
- **Why:** Frontend quality is part of the package.

### 9.5 Accessibility Audit Beyond Automated Checks 💰
- **What:** Manual audit by a screen-reader user (one paid session via Fable / friend in a11y community).
- **Cost:** Paid Fable session ~$200. Community a11y testers vary widely.
- **🆓 alternative:** Post in r/Blind asking for volunteer feedback in exchange for an acknowledgement. Or ask a KSIU disability-services contact to connect you with a screen-reader user.
- **Skip if** the budget isn't there — automated axe-core + manual keyboard nav covers ~90% of the value.

### 9.6 Internationalisation Beyond EN+AR 🆓
- **What:** Add ES, FR, ZH, JA via Crowdin or Weblate. Community translates.
- **Cost:** Crowdin and Weblate both offer free tiers for OSS projects.
- **Why:** Real product signal.

### 9.7 API Versioning Strategy Doc 🆓
- **What:** `docs/api/VERSIONING.md` — semver for the REST API, deprecation policy, sunset headers.
- **Why:** Most APIs in undergrad work have no versioning thought at all.

### 9.8 Performance Regression Tests 🆓
- **What:** Asv or pytest-benchmark in CI; alert on >10% regression.

### 9.9 Code Quality Metrics Trended 🆓
- **What:** Codacy / SonarCloud free tier wired to the repo. Track tech debt over time.
- **Cost:** Both have unlimited-OSS free tiers.

### 9.10 Architecture Decision Records (ADRs) Up to Date 🆓
- Already have `docs/adr/`. Keep adding one per major decision.

---

## 10. Security / Compliance Flex

Specific to a security tool — show you understand the same standards your customers do.

### 10.1 SOC 2 Type II Control Mapping
- **Doc:** `docs/compliance/SOC2_CONTROLS.md` — map every Trust Service Criterion (Security, Availability, Confidentiality, Processing Integrity, Privacy) to existing implementation.
- **Why:** Even "SOC 2 ready" (not certified) is a strong enterprise signal.

### 10.2 ISO 27001 Annex A Mapping
- Same exercise, ISO style.

### 10.3 NIST CSF 2.0 Mapping
- Govern / Identify / Protect / Detect / Respond / Recover — map ACR-QA capabilities.

### 10.4 CIS Controls Coverage Matrix
- Which of the 18 CIS Controls does ACR-QA contribute to?

### 10.5 Threat Model (STRIDE / Microsoft TMT) 🆓
- `docs/THREAT_MODEL.md` already exists; upgrade to a formal STRIDE-per-component model.

### 10.6 SBOM Signed & Published 🆓
- CycloneDX SBOM for every release, signed with Cosign, attached to GitHub release assets.

### 10.7 SLSA Self-Assessment 🆓
- Public self-assessment doc: where ACR-QA stands on SLSA Levels 1–3.

### 10.8 security.txt + PGP Disclosure Key 🆓
- `/.well-known/security.txt` on the hosted demo.

### 10.9 Coordinated Vulnerability Disclosure Page 🆓
- Public CVD policy. Names of disclosers acknowledged.

---

## 11. Frontier / Publishable Ideas

The kind of work that gets a co-authored paper, a job offer, or both.

### 11.1 Multi-LLM Jury 💵
- **What:** Use 3 LLMs from different providers (Groq LLaMA, Anthropic Claude, Google Gemini) for finding explanation. Majority vote on triage. Confidence = jury agreement.
- **Cost:** Groq free tier covers heavy use. Anthropic Claude API: $0–10/mo at thesis-scale evaluation. Google Gemini has a free tier (`gemini-1.5-flash` free up to 1500 req/day). **Total: ~$0–10 for the evaluation runs.**
- **🆓 alternative:** Use Groq + Gemini free tiers only, skip Claude. Still 2-of-3 jury voting works.
- **Why:** No SAST paper has compared inter-LLM agreement on triage. Publishable.

### 11.2 Differential SAST 🆓
- **What:** On a PR, only re-scan files in the diff *and* their downstream callers (via call graph). Cache everything else.
- **Why:** This is the gap commercial vendors fill with ML. You can fill it with engineering.

### 11.3 Active-Learning NR Triage 🆓
- **What:** When a NEEDS_REVIEW finding lands, the system asks the user to label it. Each label retrains the confidence scorer.
- **Why:** Closes the loop between user and tool. Publishable HCI angle.

### 11.4 Counterfactual Explanations 🆓
- **What:** For each finding, generate "this would NOT be flagged if line X looked like Y" — actionable, concrete, AI-generated diff.
- **Why:** XAI on security findings is hot in 2026.

### 11.5 LLM Embedding-Based Vulnerability Prediction 🆓
- **What:** Embed function text via an open embedding model. Compute cosine sim to known CVE descriptions. Surface high-sim functions as "look here."
- **Cost:** `sentence-transformers` runs locally on CPU — free. No API calls needed.
- **Why:** Cheap, embarrassingly parallel, lightly novel.

### 11.6 Federated Metrics Aggregation
- **What:** Privacy-preserving aggregation protocol: multiple ACR-QA deployments anonymously contribute precision/recall stats. Public dashboard of "global ACR-QA precision today."
- **Why:** Genuinely novel. Federated SAST is unstudied territory.

### 11.7 ZK-Proof Attestation
- **What:** Instead of revealing all findings, prove (zero-knowledge) that a scan ran completely and at least N findings were addressed.
- **Why:** Useful for compliance audits where the codebase is confidential. Frontier crypto + security.

### 11.8 Synthetic Benchmark Generator
- **What:** A tool that generates vulnerable code at scale — e.g. 1,000 SQL injection variants — for evaluating any SAST tool.
- **Why:** The community needs this badly. Publishable as a standalone artifact.

### 11.9 Vulnerability Knowledge Graph 🆓
- **What:** A Neo4j or RDF graph of CWE → CVE → rule → tool relationships. Visualise via cytoscape.js.
- **Cost:** Neo4j Community Edition (self-host) is free forever. Neo4j AuraDB Free has a 200k-node free tier.
- **Why:** Beautiful frontend + serious data eng + research angle.

### 11.10 Repository Trust Score
- **What:** A 0–100 score for any public repo based on history of findings, fix latency, dependency hygiene. Show on a public leaderboard.
- **Why:** This is the kind of feature that gets covered by *The Register* or *InfoQ*.

---

## 12. Outside-the-Box Wild Cards

Things that nobody's expecting and that pay off disproportionately if they land.

### 12.1 VS Code Extension 🆓
- **What:** Live ACR-QA findings shown inline in the editor. Click to see the AI explanation. Right-click to apply autofix.
- **Cost:** VS Code Marketplace publishing is free. Azure DevOps publisher account is free.
- **Why:** The IDE is where developers actually live. Marketplace listings = adoption.

### 12.2 JetBrains Plugin 💵
- Same as above for IntelliJ / PyCharm / WebStorm.
- **Cost:** JetBrains Marketplace publishing is **free for free plugins** (which yours would be). It's only paid if you monetize the plugin (revenue share). So effectively 🆓 for our case.

### 12.3 Browser Extension for GitHub PRs 💵
- **What:** Overlay ACR-QA findings on the GitHub PR diff view, without leaving the browser.
- **Cost:** Chrome Web Store **$5 one-time** developer fee. Firefox Add-ons is free. Edge Add-ons is free.
- **🆓 alternative:** Publish to Firefox and Edge only ($0). Cover Chrome users via "install unpacked" + instructions.
- **Why:** Where review actually happens.

### 12.4 Slack/Discord Bot 🆓
- **What:** `/acrqa scan <repo-url>` returns findings inline in the channel.
- **Why:** Agentic demo. Where ops actually happens.

### 12.5 CVE Filing 🆓
- **What:** During X1's live-CVE work, if you find a *previously undisclosed* vulnerability in a real OSS library, file a CVE through MITRE with you as discoverer.
- **Cost:** MITRE CVE submission is free. GitHub Security Advisory → CVE is also free.
- **Why:** "I found CVE-2026-XXXXX in production library Y" on a resume is the single highest-impact line item possible.

### 12.6 Bug Bounty Submissions Using ACR-QA 🆓
- **What:** Run ACR-QA against bug bounty in-scope targets (HackerOne / Bugcrowd). Submit findings.
- **Cost:** Free for you — you receive money if findings are accepted.
- **Why:** Real money, real validation, real CVE acknowledgements.

### 12.7 "ACR-QA Self-Scan" Public Badge 🆓
- **What:** Every commit triggers a self-scan. Result is a live badge on the README + dashboard homepage.
- **Why:** Dogfooding done loudly = trust signal.

### 12.8 Continuous Public Comparison 🆓
- **What:** A live page comparing ACR-QA, Semgrep, Bandit on a rotating set of fresh CVEs published this week. Updates daily.
- **Why:** Audacious, sustainable, and the kind of thing journalists screenshot.

### 12.9 Multi-Modal AI Triage
- **What:** Send the LLM not just the code, but a screenshot of the dashboard finding and architecture diagram. Vision-LLM gives richer triage.
- **Why:** Genuinely novel. Anthropic Claude / GPT-4V capable.

### 12.10 Agentic Remediation Loop
- **What:** Autonomous agent that detects → generates patch → runs tests → opens PR with explanation. Full Claude-style agent demo.
- **Why:** This is the demo that wins the room in 2026.

### 12.11 Live Vulnerability Heatmap of NPM/PyPI 🆓
- **What:** Daily scan of top-100 PyPI + top-100 npm packages. Public heatmap of "today's most-bug-laden popular package."
- **Why:** News-worthy. Reproducible. Free marketing forever.

### 12.12 TLA+ Specification of Quality-Gate Semantics
- **What:** Formally specify the quality-gate state machine. Prove no-false-pass property.
- **Why:** Formal methods in a real product. Senior architect signal.

### 12.13 ACR-QA at Conferences Live-Streamed
- **What:** When you do a meetup or conference talk, live-stream it. Build a YouTube channel.

### 12.14 Podcast Appearances
- Pitch yourself to security podcasts: SecurityNow, DarkNet Diaries (long shot), AppSec Insiders, Open Source Security Podcast.

---

## 13. Priority Stack — If We Had to Pick

If you only do 10 things from this entire document, do these (in approximate chronological order):

| # | Lane | Item | Why |
|---|------|------|-----|
| 1 | §2.4 | "1,942 → 55" funnel reveal slide | One slide = whole thesis. Free. |
| 2 | §3.1 | Public hosted demo at `acrqa.<domain>` | Foundation for everything external. |
| 3 | §5.1 | Five-rater κ study | Closes the only "in progress" eval claim. |
| 4 | §2.2 | Live exploit demo with backup video | Memorable defense moment. |
| 5 | §4.1 | Cosign + SLSA L3 + Rekor | Industry-leading supply chain story. |
| 6 | §6.1 | Hacker News post day after defense | External validation that lasts. |
| 7 | §5.4 | Submit to OWASP AppSec Days | "Submitted to" line on thesis. |
| 8 | §3.2 | GitHub webhook receiver | Production-grade adoption demo. |
| 9 | §12.1 | VS Code extension | Where devs actually work. |
| 10 | §12.5 | File a real CVE | Resume gold. |

These ten are mutually reinforcing — every one feeds the others.

---

## 14. Anti-Plan — Things to Explicitly NOT Do

Some seductive directions that would waste 25 weeks:

- **Don't rewrite the backend in Go/Rust.** The committee doesn't care, hiring managers don't care, and you'll burn a month.
- **Don't add 20 more SAST tools.** Diminishing returns. The 19 you have is already novel.
- **Don't refactor for refactoring's sake.** Every refactor risks the 100% recall claim. Refactor only when adding a new lane requires it.
- **Don't chase paid features unless they ship.** Stripe integration without 10 paying users = signal-less.
- **Don't enter every conference.** Pick 2; do them well.

---

## 15. Cadence

- **Weekly review:** every Sunday, mark lanes as ⏳ / ✅ / ❌.
- **Monthly snapshot:** publish a public "ACR-QA Monthly" post — what shipped, what's next.
- **Quarterly retrospective:** at week 12 and week 24, revisit this doc and re-prioritise based on what's worked.

---

## 16. Success Metrics — What "Best in University" Looks Like

| Metric | Floor (passing) | Target (best in uni) | Stretch (publishable / hireable) |
|--------|-----------------|----------------------|----------------------------------|
| Defense grade | A | A+ | A+ with commendation |
| GitHub stars | 0 | 50 | 500+ |
| HN front page | — | Yes | Top 10 |
| Submitted papers | 0 | 1 | 2 accepted |
| Public deployments | 0 | 5 (friends, peers) | 50+ (strangers) |
| Inter-rater κ | — | 0.78 | 0.85+ |
| Demo URL traffic | — | 100 visits | 10,000 visits |
| CVE filed | 0 | 0 | 1+ as discoverer |
| Resume-worthy bullets | 5 | 10 | 20+ |
| Job offers post-defense | 0 | 1 | "weighing offers" |

---

## 16.5 Total Money Required — Summary

If you do the entire top-10 priority stack from §13 with **everything-must-be-free** discipline:

| Item | Cost | Notes |
|------|------|-------|
| §2.4 Funnel reveal slide | 🆓 | — |
| §3.1 Public hosted demo | 🆓 / **$10/yr** | Free with default Railway URL; $10/yr if you want a custom domain |
| §5.1 Five-rater κ study | 🆓 | — |
| §2.2 Live exploit demo | 🆓 | — |
| §4.1 Cosign + SLSA L3 + Rekor | 🆓 | — |
| §6.1 Hacker News post | 🆓 | — |
| §5.4 OWASP AppSec Days submission | 🆓 | Submission is free; only pay if accepted and you want to attend in person |
| §3.2 GitHub webhook receiver | 🆓 | — |
| §12.1 VS Code extension | 🆓 | — |
| §12.5 File a real CVE | 🆓 | — |
| **Grand total top-10** | **$0–$10** | Literally a fast-food meal |

**Optional add-ons if you have a small budget:**

| Optional | Cost | Worth it? |
|----------|------|-----------|
| Chrome Web Store one-time fee | $5 | Yes — if you ship the browser extension |
| Conference registration (if accepted) | $200–$400 student rate | Only if presenting in person; virtual usually cheaper or free |
| Multi-LLM jury Claude API | $0–$10/mo | Yes — frontier-research feel for low cost |
| Paid screen-reader a11y session | $200 | Skip — automated tools cover 90% |
| Bug bounty payouts | $150–$1,500 | Skip — use acknowledgement-only "Hall of Fame" instead |

**Bottom line:** You can execute 95% of this plan for **under $20 total**. The expensive items (compliance audits, paid pen-tests, conference travel) are explicitly marked and skippable. Don't let the size of the plan make you think it requires a budget — it doesn't.

---

## 17. Invocation

This plan is modular. Each section can be picked up independently. Tell me which section to deep-dive next, and we'll spec the implementation in detail — the same way V3 and V4 were planned and shipped task-by-task.

Recommended next conversation: **§2 (Defense Stagecraft) + §3.1 (Public Demo)** — these two together give you a working external demo and a memorable defense in ~3 weeks.

---

*Plan v5 supersedes nothing — V3 (technical foundation) and V4 (empirical battery) are complete. V5 is the meta-layer: validation, polish, and amplification.*

*Last updated: 2026-05-31. Status markers added as lanes land.*
