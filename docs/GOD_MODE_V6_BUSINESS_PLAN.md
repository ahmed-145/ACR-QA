# ACR-QA God Mode Plan v6 — From 4/10 Product to 10/10 Company

> **Created:** 2026-06-02
> **Author:** Ahmed Mahmoud Abbas
> **Lens:** This is NOT a thesis plan. This is a harsh, founder/VC-grade plan that treats ACR-QA
> as a startup that has to win a real, crowded, well-funded market. Engineering craft is already
> an 8/10. This document is about closing the 2/10 → 10/10 gap on **product and business**.
>
> **Companion docs:** `GOD_MODE_V5_PLAN.md` (academic + portfolio + adoption) and
> `ACTIVE_ROADMAP.md` (the free, fresh-grad execution list). v6 sits *above* both: it decides
> *what the company is*, then those plans become tactics underneath it.

---

## 0. The Brutal Scorecard (why it's a 4/10 today)

| Dimension | Score | Why |
|-----------|:----:|-----|
| Engineering craft | 8/10 | 2,757 tests, CI, dogfooding, multi-language, taint, attestation. Genuinely strong. |
| **Moat / defensibility** | **2/10** | Detection is rented from OSS (ruff, bandit, semgrep, gosec). Differentiation is the *commodity* layer (AI explanations) that incumbents already ship. |
| **Wedge / positioning** | **2/10** | "Everything SonarQube does, plus AI, plus taint, plus CBOM, plus provenance." No ICP, no single sentence. Feature sprawl = built inward, not toward a customer. |
| **Proof / evidence** | **3/10** | 97.1% precision on self-chosen corpora; 96.4% on n=55. Self-graded, unfalsified, zero third-party validation, zero real users. |
| **Business model** | **2/10** | "$0 recurring, free-tier Groq" is unsellable to enterprise — no SLA, no data guarantees, rate-limited. The thing that makes it cheap makes it un-monetizable. |
| **Distribution / GTM** | **4/10** | PyPI + GitHub Action + VS Code ext + Docker exist. Good hooks, zero pull, no users, no motion. |
| **Market timing** | **9/10** | AI-code vuln explosion (+107% vulns/codebase YoY) + SAST alert-fatigue crisis + supply-chain provenance gold rush. The wind is at your back. **This is the saving grace.** |

**Weighted product/business score: ~4/10.** The market (9) and craft (8) are carrying a strategy (2)
that has no edge. **You don't have a product problem. You have a *focus* problem.**

---

## 1. The Market Reality (researched 2026-06-02)

- **Market size:** Narrow AI-PR-review category ≈ **$400–600M ARR**, growing **30–40% YoY**. Broad
  code-quality + SAST + AI-assistant review ≈ **$2–3B**, growing 25–30%. [Sacra / Sourcegraph]
- **Funding heat:** CodeRabbit hit **$40M ARR (Apr 2026, +700% YoY)**, **$550M post-money** Series B.
  Greptile $25M Series A (Benchmark). Snyk Code / Checkmarx / Semgrep all bolted AI onto SAST.
- **The pain that's unsolved:** Traditional SAST = **30–70% false positives**. Single SAST tools
  catch **<22%** of real vulns. Alert fatigue means real bugs die in the noise. *Nobody has won
  "trust" yet.*
- **The tailwind:** AI-generated code is **25.1% flawed**, **1.88× more vulnerable** than human code;
  mean vulns/codebase **+107% YoY**; production incidents/PR **+23.5%** in one quarter. The *volume*
  of code-to-review is exploding faster than humans can review it.
- **Where smart money is going:** Endor Labs' headline feature is **reachability** — *70–80% fewer
  actionable findings*. Chainguard + Endor ship **SLSA L3 provenance + verified trust badges**.
  Anthropic shipped **Claude Code Security** (Feb 2026). The frontier is **precision + provenance +
  AI-code-native**, not "more rules."

**Translation:** The market is not asking "who finds the most issues?" That war is lost to incumbents
and OSS. The market is asking **"who do I trust enough to block a merge automatically?"** Whoever owns
*trust* — verifiable, low-FP, provable — wins the next cycle. **You already built the pieces of that
answer and then hid them.**

---

## 2. The One-Sentence Bet (the wedge)

> **ACR-QA is the trust layer for AI-written code: every finding it surfaces is exploit-verified and
> cryptographically attested, so you can auto-block merges without alert fatigue and prove it to an
> auditor.**

Unpack the three non-negotiable nouns:

1. **Trust layer** — not "another scanner." We sit *on top of* OSS scanners + AI assistants and answer
   the only question that matters at merge time: *is this real, and can I act on it automatically?*
2. **Exploit-verified** — the **Confirmed Tier** (already 96.4% precision, n=55) + the X2 exploit-
   verification harness (SQLi/cmdinj/SSTI proven in a Docker sandbox) is the product's *spine*, not a
   thesis appendix. "We don't report it unless we can show it firing."
3. **Cryptographically attested** — every verdict is ECDSA-signed, logged to Sigstore Rekor, SLSA L3.
   This is the **moat** and the compliance wedge. Incumbents *explain*; almost none *attest*.

**Everything in the codebase that doesn't serve this sentence gets demoted to "platform depth," not
headline.** CBOM, radon complexity, dead-code — they stay in the product as supporting signal; they
leave the pitch.

---

## 3. The ICP (exactly one, to start)

Stop selling to "developers." Sell to a person with a budget and a board-level fear.

**Primary ICP — "The AppSec lead at a Series B–D company shipping AI-assisted code."**
- 50–300 engineers, heavy Copilot/Cursor/Claude Code usage → drowning in AI-generated PRs.
- Has a SAST tool already (Snyk/Semgrep/SonarQube) that the devs **ignore** because of FP noise.
- Is personally accountable for SOC2 / ISO 27001 / FedRAMP / EU CRA evidence.
- **Pain (in their words):** "I can't make engineers fix findings they don't trust, and I can't prove
  to the auditor that our review process actually happened."

**Why this ICP is right:**
- They have budget (security line item, not eng tooling).
- They feel two pains you uniquely solve: **trust** (Confirmed Tier) + **provenance** (attestation).
- They're a *wedge into* the broader dev-tool market later — land in security, expand to all PRs.

**Beachhead even narrower (first 10 design partners):** open-source maintainers and small AI-native
startups already on GitHub Actions — zero procurement, instant install, public logos, fast feedback.
Use them to manufacture the proof (Section 6) that lets you sell the paying ICP.

**Anti-ICP (say no on purpose):** enterprises wanting full SAST replacement, regulated orgs needing
on-prem air-gap on day one, anyone who wants "max recall." Not now.

---

## 4. Positioning & Messaging (kill the "plus" disease)

| Replace this... | ...with this |
|---|---|
| "Provenance-first AI code review platform with 10+ tools" | "Auto-block merges you can actually trust — and prove." |
| "97.1% precision across 4 repos" | "We only flag what we can exploit. 96% of what we surface is real — verified, not estimated." |
| "RAG-grounded explanations, CBOM, taint, confidence scoring..." | (depth shown *after* the click, never in the headline) |
| "$0 recurring cost" | "Predictable per-seat pricing. Your code never trains anyone's model." |

**Category to own:** not "SAST," not "AI code review" — **"Merge Trust / Verified Findings."** Be the
first name in a category you define. Endor owns "reachability"; you own **"exploit-verified +
attested."** One word in the buyer's head: **trustworthy.**

**The demo that closes:** side-by-side. Left: Semgrep/Snyk dumps 40 findings on a PR. Right: ACR-QA
shows **3 Confirmed**, each with a **live exploit replay** (the {{7*7}}=49 / `OR 1=1` leak) and a
**"Verify this attestation" button** that resolves the signature on Rekor. The buyer's gut reaction:
*"oh — I could turn this one on as a required check."* That gut reaction is the whole company.

---

## 5. The Moat Thesis (how a 2 becomes a 9)

Orchestration of OSS is a weekend for a funded team — **accepted**. So the moat is not the scanners.
The moat is the **layers a competitor can't copy by adding an API key:**

1. **Verification data flywheel.** Every exploit-verification run (pass/fail, in sandbox) is labeled
   ground truth. Accumulate a proprietary corpus of *"finding → did it actually exploit?"* across
   real customer code. That dataset trains a verifier nobody else has. **This is the real moat — build
   the data loop now, even at tiny scale.**
2. **Attestation as a network/compliance lock-in.** Once a customer's audit trail, SOC2 evidence, and
   merge-gate policy depend on ACR-QA signatures in Rekor, switching cost is *contractual and
   regulatory*, not technical. Provenance is sticky in a way explanations never are.
3. **Trust calibration per-org (triage memory).** The suppression-learning + confidence model already
   in the codebase becomes *org-specific* — the longer they run it, the better-tuned to their code,
   the worse a cold-start competitor performs against an incumbent ACR-QA install.
4. **Category ownership + standard.** Publish the "Verified Finding" spec (open schema: claim +
   exploit evidence + signature). If others adopt your attestation format, you're the standard. Moats
   made of standards (cf. Sigstore, SLSA) are the strongest a small team can build.

**Priority order to build moat:** #1 (data loop) → #2 (attestation lock-in) → #4 (standard) → #3
(per-org tuning). #1 starts the day you get your first design partner.

---

## 6. The Proof Plan (de-risk the metrics — 3 → 9)

Self-graded numbers are worthless to a buyer or investor. Manufacture *adversarial, third-party,
reproducible* proof.

- **P-1 — Independent benchmark on a corpus you didn't pick.** Run on OWASP Benchmark, the Juliet
  Test Suite, and the SecurityEval / LLMSecEval AI-code datasets. Publish precision/recall **with CI
  bands** vs. Snyk Code, Semgrep, SonarQube, and CodeQL on the *same* corpus. Pre-register the
  methodology (you already do this for thesis — reuse it).
- **P-2 — Public live leaderboard.** A page that re-runs the benchmark weekly in CI and publishes
  results signed + timestamped. "Our numbers are continuously falsifiable" is itself the marketing.
- **P-3 — Design-partner case studies (n≥5).** Real repos, real before/after: "X had 312 SAST
  findings, devs fixed 4%. After ACR-QA Confirmed Tier: 11 findings, 9 fixed, 0 disputed." That one
  sentence sells better than any precision number.
- **P-4 — A real CVE filed from a real scan.** Nothing converts skeptics like "ACR-QA found
  CVE-2026-XXXXX in [popular OSS package]." Hunt for it deliberately; you have the recall battery
  muscle already.
- **P-5 — Third-party security audit of ACR-QA itself.** The trust company must be trustworthy. A
  public pentest report + the self-scan badge = practice-what-you-preach proof.

**Each proof item moves a specific objection from "unproven" to "shown." Sequence: P-1 → P-3 → P-4 →
P-2 → P-5.**

---

## 7. Product Reframe — Surface / Bury / Build

**SURFACE (make these the entire first impression):**
- Confirmed Tier as the *default* view. The 1,942 → 55 funnel is the hero visual.
- Exploit replay (X2) as a clickable artifact on every Confirmed finding.
- "Verify attestation" button → resolves on Rekor in front of the user.
- PR check: one number — *"N findings you can trust"* — as a required GitHub status check.

**BURY (keep in code as depth, remove from pitch):**
- CBOM / quantum-crypto, radon complexity, dead-code, the 327-rule breadth, multi-language-for-its-
  own-sake. These are "platform maturity" footnotes, not headlines. They *support* trust; they don't
  *sell* it.

**BUILD (net-new, in priority order):**
1. **Reachability-gated Confirmed Tier++** — fuse the existing taint + dependency-reachability +
   path-feasibility engines into the verification gate so "Confirmed" also means "reachable from a
   real entry point." This is the Endor-killer feature you already have parts of — assemble it.
2. **The verification data loop** — log every verify-pass/fail as labeled data (Moat #1). Minimal:
   a table + an export. Do this *first*; it compounds.
3. **AI-code-native mode** — ingest the diff of a Copilot/Cursor/Claude PR and report *only* what the
   AI introduced (differential SAST, already prototyped). Position squarely at the +107% AI-vuln
   wave.
4. **Policy-as-attestation** — `.acrqa.yml` gate decisions get signed too, so "this PR was allowed to
   merge under policy vX" is itself an audit artifact. Turns your policy engine into compliance gold.
5. **SARIF + GitHub Advanced Security + GitLab interop** — meet the buyer where their evidence already
   lives; don't make them adopt a new dashboard to get value.

---

## 8. Business Model (2 → 9: kill the free-tier dependency)

The free-tier Groq story must die for the *paid* product. Architecture stays cheap; the *offer* must
be enterprise-credible.

**Pricing (land-and-expand):**
- **Free / OSS** — public repos, GitHub Action, Confirmed Tier, community attestation. *Top-of-funnel
  + data flywheel fuel.* (This is where free-tier LLM is fine.)
- **Team — $X/dev/mo** — private repos, org-tuned triage memory, SARIF/GHAS export, SSO, your own LLM
  key (BYO-key removes the cost objection *and* the data objection at once).
- **Enterprise — annual contract** — signed attestation archive, compliance evidence packs (SOC2/ISO/
  EU CRA), on-prem/VPC deploy, SLA, audit-log retention, dedicated verifier model. *This* is where
  the attestation moat monetizes — you're selling *evidence*, not scanning.

**Why this works:** the moat (attestation + verification data) lives in the *paid* tiers; the OSS tier
feeds the flywheel and GTM. You sell **trust and proof**, which has *security-budget* willingness-to-
pay, not *dev-tool* price sensitivity.

**The metric that matters:** not stars, not scans — **"% of Confirmed findings the customer actually
fixed."** That's the trust KPI. If it's >70%, you have a company. Instrument it from day one.

---

## 9. GTM Motion

- **Bottom-up wedge:** GitHub Action free tier → maintainers + AI-native startups install in 2 min →
  Confirmed Tier "wow" → public attestation badges on their README = distribution loop.
- **Content as a moat-builder:** publish the AI-code vuln study (X3) and live-CVE work as *industry
  research*, not thesis chapters. "We scanned 400 LLM outputs; here's the FP-free way to review AI
  code." This is exactly the content the market is searching for right now.
- **Land in security, expand to eng:** AppSec lead buys for trust + compliance; once it's a required
  check, every dev touches it on every PR. Classic wedge expansion.
- **Design-partner program (first 10, free, hand-held):** trade white-glove onboarding for logos,
  case studies (P-3), and verification-loop data. This is the single highest-leverage activity for
  the next 90 days.

---

## 10. Competitive Teardown (know exactly why you win each fight)

| Competitor | Their strength | Your wedge against them |
|---|---|---|
| **Snyk Code** | Brand, SCA+SAST breadth, enterprise sales | They estimate severity; you *exploit-verify* + *attest*. Sell "0 disputed findings." |
| **Semgrep** | Deterministic engine, custom rules, dev love | You orchestrate Semgrep *and* add the trust/attestation layer on top — partner, don't fight the engine. |
| **CodeRabbit** | $40M ARR, AI-PR UX, momentum | They review *style + bugs* broadly with AI (and its FP risk); you own *security findings you can auto-block*. Different job-to-be-done. |
| **Endor Labs** | Reachability, supply-chain, funding | Closest threat. They do reachability for SCA; you do exploit-verification + attestation for *first-party code*. Reachability-gate your Confirmed Tier to neutralize their headline. |
| **GitHub Advanced Security / CodeQL** | Distribution, native | You *feed* GHAS via SARIF and add attestation it lacks. Be the trust layer *inside* their ecosystem. |
| **Claude Code Security / Cursor BugBot** | Frontier model, logic-bug depth, distribution | They find subtle bugs but with no provenance and unknown FP discipline. You're the *verification + attestation* layer over agentic findings — including theirs. |

**Recurring pattern:** almost everyone *finds*; almost no one *verifies + attests*. Stand exactly
there. Where you can't win on detection, **integrate and sit on top** (Semgrep, GHAS, Claude) rather
than compete.

---

## 11. Phased Execution — how the score climbs 4 → 10

Each phase has an **exit metric** and the **score it unlocks**. Don't start a phase until the prior
exit metric is real.

### Phase 0 — Refocus (Weeks 0–4) → product score 4 → 5
- Rewrite the entire surface (README, landing, dashboard default) around the **one sentence** (§2).
- Ship the **side-by-side Confirmed-vs-noise demo** (§4) as a 90-second public video + live page.
- Assemble **reachability-gated Confirmed Tier** from existing engines (Build #1, §7).
- Stand up the **verification data loop** table (Build #2 / Moat #1).
- **Exit metric:** a stranger watches the demo and says *"I'd turn that on as a required check."*

### Phase 1 — Proof (Weeks 4–12) → 5 → 7
- P-1 independent benchmark (OWASP/Juliet/SecurityEval) vs. 4 named tools, CI bands, pre-registered.
- Recruit **5 design partners** (beachhead ICP); white-glove onboard; start the data flywheel.
- Ship **AI-code differential mode** (Build #3) — ride the +107% wave.
- **Exit metric:** ≥3 written case studies (P-3) + a public benchmark page beating ≥1 incumbent on
  precision *at equal recall band*.

### Phase 2 — Monetize (Weeks 12–24) → 7 → 8
- Ship **BYO-LLM-key + private repos + SARIF/GHAS export + SSO** (the Team tier, §8).
- Land **first 3 paying Team customers** from the design-partner cohort.
- Publish the **AI-code vuln research report** as industry content (GTM, §9).
- Instrument and report the **"% Confirmed fixed"** KPI (target >70%).
- **Exit metric:** first real revenue + KPI >70% on ≥3 orgs.

### Phase 3 — Moat & Standard (Weeks 24–40) → 8 → 9
- Publish the **"Verified Finding" open spec** (claim + exploit evidence + signature) (Moat #4).
- Ship **compliance evidence packs** (SOC2/ISO/EU CRA) — the Enterprise wedge (§8).
- File **≥1 real CVE** from a customer/OSS scan (P-4).
- Third-party pentest of ACR-QA (P-5).
- **Exit metric:** one Enterprise contract *and* one external party adopts/cites the Verified Finding
  spec or attestation format.

### Phase 4 — Scale the wedge (Weeks 40+) → 9 → 10
- Expand from security-only to "every PR" inside landed accounts (wedge expansion).
- Verification data loop large enough to train a **proprietary verifier** that measurably beats the
  rule-only baseline — the compounding moat realized.
- **Exit metric:** net revenue retention >120% in landed accounts + a verifier model whose precision
  edge over OSS-only is *measured and published*. **This is 10/10:** defensible moat (data + standard),
  proven (third-party + revenue), focused (one wedge), monetized (security budget), with the market
  wind still blowing.

---

## 12. Scorecard — what 10/10 actually requires

| Dimension | Today | 10/10 looks like | Gets there in |
|---|:--:|---|:--:|
| Moat | 2 | Proprietary verification dataset + attestation lock-in + an adopted standard | Phase 3–4 |
| Wedge/positioning | 2 | One sentence, one ICP, owns the word "trustworthy" | Phase 0 |
| Proof | 3 | Third-party benchmarks w/ CI + ≥5 case studies + a filed CVE + external audit | Phase 1–3 |
| Business model | 2 | Security-budget pricing, BYO-key, evidence-pack Enterprise tier, NRR>120% | Phase 2–4 |
| Distribution | 4 | Self-serve OSS loop + design-partner→paid motion + research-content engine | Phase 1–2 |
| Market timing | 9 | (Already there — just don't waste it) | Now |

**The single highest-leverage move this quarter:** Phase 0 + recruiting design partners. Everything
else compounds off having real users generating real verification data and real case studies. Focus
beats features. **Pick the sentence. Delete the rest from the pitch. Go.**

---

## 13. Kill Criteria (intellectual honesty — when to pivot)

- If, after 10 design partners, **"% Confirmed fixed" stays <50%**, the trust wedge isn't real →
  pivot to pure AI-code-diff review or to the attestation/compliance angle as the *primary* product.
- If independent benchmarks (P-1) show ACR-QA **can't beat any incumbent at equal recall**, the
  Confirmed Tier isn't differentiated enough → double down on *reachability + attestation* as the
  whole story, drop the precision claim.
- If attestation generates **zero pull in buyer conversations** across 10 calls, provenance is a
  vitamin not a painkiller here → demote it to a feature and lead with AI-code-diff precision.

**A 10/10 isn't "we built everything." It's "we bet the one thing that's true, proved it to outsiders,
and made the market pay for it." You already have the engine. This plan is about pointing it at one
target.**

---

## Sources (market research, 2026-06-02)

- [Sacra — CodeRabbit revenue, valuation & funding](https://sacra.com/c/coderabbit/)
- [Sourcegraph — 13 Best Automated Code Review Tools in 2026](https://sourcegraph.com/blog/automated-code-review-tools)
- [Endor Labs × Chainguard — End-to-End Software Supply Chain Security](https://www.endorlabs.com/learn/endor-labs-and-chainguard-partner-to-deliver-end-to-end-software-supply-chain-security)
- [Practical DevSecOps — SLSA Framework Guide 2026](https://www.practical-devsecops.com/slsa-framework-guide-software-supply-chain-security/)
- [Offensive360 — AI-Powered SAST: The Future of Code Security in 2026](https://offensive360.com/blog/ai-powered-sast-future-code-security-2026/)
- [CodeAnt — How Accurate Is AI Code Review in 2026?](https://www.codeant.ai/blogs/ai-code-review-accuracy)
- [Paperclipped — AI-Generated Code Security Vulnerabilities 2026](https://www.paperclipped.de/en/blog/ai-generated-code-security-vulnerabilities/)
- [Arnica — Top 6 AI SAST Tools for 2026](https://www.arnica.io/blog/top-6-ai-sast-tools-for-2026-the-quick-guide-to-agentic-static-application-security-testing)
- [DevOps.com — Claude Code Security Catches Vulnerabilities While You Write Code](https://devops.com/claude-code-security-catches-vulnerabilities-while-you-write-code/)
</content>
