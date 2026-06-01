# ACR-QA Active Roadmap — Ahmed's Personal Execution Plan

> **What this is:** The actual list Ahmed is executing. Everything here is **completely free** (no domain, no card, no surprise bills) and **realistic for a fresh-grad backend + DevOps engineer**.
>
> **What this is NOT:** A wish list. The full menu lives in [`GOD_MODE_V5_PLAN.md`](GOD_MODE_V5_PLAN.md) — pick from there in future years.
>
> **Created:** 2026-05-31
> **Horizon:** ~25 weeks (defense day is one waypoint, not the finish line)
> **Total cost:** $0 ongoing. Possibly $0 setup.

---

## The 15 Items I'm Actually Doing

| # | Item | Time | Status | Why this one |
|---|------|------|--------|--------------|
| 1 | **Funnel reveal slide** (1,942 → 55 → 96.4% precision) | 1 hour | 📋 | One slide = whole thesis. Highest ROI in the plan |
| 2 | **Docker image on `ghcr.io/<user>/acrqa`** | 2 days | 📋 | Free forever; replaces hosted demo; one-liner install |
| 3 | **5-min demo video on YouTube** | 1 day | 📋 | Lives forever; link from HN/LinkedIn/thesis |
| 4 | **README GIFs + Codespaces "Open in" button** | 1 day | 📋 | Interactive demo with zero hosting cost |
| 5 | **Cloudflare Pages static dashboard** at `acrqa.pages.dev` (mock data) | 2 days | 📋 | One URL to point at; truly free + free SSL + custom subdomain |
| 6 | **5-rater κ study** (closes the "in progress" eval gap) | 2.5 weeks elapsed | 📋 | Recruit 5 KSIU peers/faculty; finishes the only weak claim |
| 7 | **GitHub webhook receiver** (PR → autoscan → comment) | 1–2 weeks | 📋 | Best single backend portfolio piece |
| 8 | **VS Code extension** (free Marketplace listing) | 1–2 weeks | 📋 | "Find me on the Marketplace" line on resume |
| 9 | **Multi-LLM jury** (Groq + Gemini free tiers only) | 3 days | 📋 | Frontier-feel for trivial work |
| 10 | **Cosign + SLSA L3 + Sigstore Rekor** | 2 days | 📋 | Senior DevOps story via copy-paste GitHub Action |
| 11 | **Self-scan badge** on README | 1 hour | 📋 | Public dogfooding signal |
| 12 | **Hacker News post + LinkedIn article + blog** | 1 day | 📋 | External validation that lasts a lifetime |
| 13 | **Differential SAST** — new-only findings vs. last scan (§11.2) | 3–5 days | 📋 | `fingerprint NOT IN (prev_run)` query; instant CI value, easy to demo |
| 14 | **Counterfactual explanations** — "what would fix this?" per finding (§11.4) | 3–5 days | 📋 | Free with an LLM prompt; makes AI enrichment feel frontier-level |
| 15 | **Kubernetes operator with CRDs** — `ACRQAScan` custom resource (§4.8) | 2–3 weeks | 📋 | The DevOps showpiece; "runs natively in k8s" line on resume |

**Total work:** ~8–9 weeks of focused effort
**Total ongoing cost:** $0
**Total setup cost:** $0 (no card required for any of the above)

---

## Suggested 25-Week Rhythm

| Weeks | Focus | Why this order |
|-------|-------|----------------|
| **1** | #1 funnel slide + #11 self-scan badge + #10 Cosign/SLSA | Quick wins. Start recruiting κ raters in parallel |
| **2–3** | #2 GHCR Docker image + #3 demo video + #4 README polish | "Installable demo" story complete |
| **4** | #5 Cloudflare Pages static dashboard | One URL to point at |
| **5–6** | #7 GitHub webhook receiver | The backend showpiece |
| **6–7** | #13 Differential SAST | Natural follow-on to webhook; "only show NEW findings" |
| **7** | #9 Multi-LLM jury + #14 Counterfactual explanations | Both are LLM prompt additions; ship together in one week |
| **8–9** | #8 VS Code extension | IDE marketplace listing |
| **10** | #6 5-rater κ analysis (raters submit by week 9) | Closes the eval gap |
| **11+** | Defense + #12 HN/LinkedIn/blog the day after | External validation |
| **12–14** | #15 Kubernetes operator with CRDs | DevOps showpiece; do after defense pressure is off |
| **15–25** | **Buffer.** Finals, job hunting, illness, serendipity (CVE discovery, paper acceptance, HN front page) | Real life never goes to plan |

---

## Why I'm NOT Doing These (deferred to "upcoming years")

These are great items but wrong-level for fresh-grad scope. They live in [`GOD_MODE_V5_PLAN.md`](GOD_MODE_V5_PLAN.md) and I'll revisit them when I'm 1–3 years into industry.

### Deferred — "advanced backend/distributed-systems patterns"
- §3.6 Multi-tenancy (real RBAC + orgs)
- §3.8 gRPC sidecar
- §3.9 Event-sourced scan history
- §3.10 CQRS split

### Deferred — "platform / staff-engineer level DevOps"
- §4.9 OPA Gatekeeper integration
- §4.10 Service mesh + Vault mTLS PKI
- §4.13 PostgreSQL streaming replication + PITR
- §4.14 Cloud KMS-backed ECDSA

### Deferred — "compliance paperwork"
- §10.1–10.4 SOC 2 / ISO 27001 / NIST CSF / CIS Controls mappings

### Deferred — "academic-flex without portfolio value"
- §5.6 TLA+ formal spec
- §12.12 TLA+ quality-gate spec

### Deferred — "frontier research that takes months"
- §11.6 Federated metrics aggregation
- §11.7 ZK-proof attestation
- §11.8 Synthetic benchmark generator
- §11.10 Repository trust score with live leaderboard
- §12.9 Multi-modal AI triage
- §12.10 Full agentic remediation loop

### Deferred — "needs budget I don't have"
- §8.6 Bug bounty payouts (using free "Hall of Fame" acknowledgement-only alternative if needed)
- §9.5 Paid a11y session (using free community-volunteer alternative if needed)
- §5.4 Conference attendance (submission is free; only travel/registration is paid)

### Deferred — "good but low-priority for fresh grad"
- §3.4 GraphQL endpoint (REST is fine)
- §3.5 Plugin system
- §3.7 WebSocket (SSE is fine)
- §4.2 ArtifactHub/Terraform Registry publishing (do once #2 GHCR works)
- §7.x Product/business docs (need real users first)
- §8.x OSS community building (empty Discord is worse than no Discord)
- §11.3 Active learning (needs labelled dataset + model training pipeline — months of work)
- §11.4 Counterfactual explanations → moved to active list (#14)
- §12.2 JetBrains plugin (do after VS Code if I have time)
- §12.3 Browser extension (do after VS Code if I have time)

---

## Free Service Account Setup Checklist (Week 1)

To execute the 15 items, I need accounts on these services. All free, all no-card-required unless noted:

- [ ] **GitHub Container Registry** (`ghcr.io`) — uses existing GitHub account, free for public images
- [ ] **YouTube** — free, uses Google account
- [ ] **Cloudflare** — free tier, free Pages, free SSL, **no card required** for the free tier
- [ ] **Sigstore Cosign + Rekor** — free public-good service, no account needed
- [ ] **VS Code Marketplace publisher** — free, uses Azure DevOps account (free, no card)
- [ ] **Groq Console** — free tier already in use (existing)
- [ ] **Google AI Studio** (Gemini API) — free tier, **no card required**
- [ ] **OSF (Open Science Framework)** — free academic account for pre-registration
- [ ] **Zenodo** — free, for the DOI when I eventually upload the replication package
- [ ] **Hacker News** — free, just create account a week before defense to age it
- [ ] **LinkedIn** — already have it (presumably)

**Optional later (defer until ready):**
- [ ] **MITRE CVE Numbering Authority** — only if I find a real undisclosed vuln through X1 (§12.5)
- [ ] **HackerOne** — only if I want to submit bug bounty findings (§12.6)

---

## Success Definition for This Roadmap

The plan succeeds if, **by the end of week 11 (defense day)**:

| Floor (passing) | Target | Stretch |
|-----------------|--------|---------|
| Defense graded A | Defense A+ | A+ with commendation |
| #1–#12 shipped | #1–#14 shipped | All 15 + HN front page |
| Public GHCR image | + Cloudflare static demo URL | + VS Code Marketplace listing |
| 5-rater κ ≥ 0.78 | κ ≥ 0.85 | κ ≥ 0.90 |
| Demo video uploaded | + ≥ 100 views | + ≥ 1,000 views |
| HN post submitted | + reached front page | + top 10 |
| Resume updated with project | + 3 hiring conversations | + 1 written offer |
| — | K8s operator (#15) live | K8s operator + published blog post |

**Anything past defense day = bonus, not required.**

---

## Cadence

- **Weekly check-in:** Sunday evening — mark items 📋 → 🚧 → ✅. Move blocked items to ❓ with one-line "why blocked."
- **Mid-cycle review (week 6):** Re-read this doc. Is the 15-item list still right? Anything to add or drop?
- **Post-defense retro:** what worked, what didn't, what to revisit from `GOD_MODE_V5_PLAN.md` in the coming year.

---

## Important Rules I'm Setting for Myself

1. **No money out.** If something requires a card or threatens to bill me, I find a free alternative or skip it.
2. **No "while I'm at it" scope creep.** Each of the 15 items has a defined "done" criterion. I ship and move on.
3. **No item from "Deferred" without writing it down here first.** If something deferred starts looking tempting, I update this doc and move it into the active list, *and* move something out. The list stays at 15 or fewer.
4. **Defense day is a milestone, not a deadline.** If something slips, I have 14 weeks of buffer. I will not panic-ship anything for defense.
5. **External validation comes after technical work.** No HN post until #2–#11 are at least partially shipped. No HN post on a half-built demo.

---

## When in Doubt

- The thesis is already done. The numbers (96.4% / 100% / F1=98.2%) are real. This roadmap is about polish, validation, and adoption — not new features.
- Do the single highest-leverage thing on this list today. Don't read more plans. Don't browse more options. Do #1, then #2, then #3.
- The full ambition lives in [`GOD_MODE_V5_PLAN.md`](GOD_MODE_V5_PLAN.md). When this 15-item list is fully ✅, come back, pick another lane, and repeat.

---

*Active roadmap updated 2026-06-01. Updated weekly until all 15 items are ✅.*
*See [`GOD_MODE_V5_PLAN.md`](GOD_MODE_V5_PLAN.md) for the full strategic menu.*
