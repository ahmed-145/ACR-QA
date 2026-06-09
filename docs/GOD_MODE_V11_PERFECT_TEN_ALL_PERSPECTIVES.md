# ACR-QA God Mode v11 — Perfect Ten Across Both Scoreboards (Thesis + Startup)

> **Created:** 2026-06-09 · **Author:** Ahmed Mahmoud Abbas · **Defense:** 2026-06-25
> **Trigger:** "Rate as a product AND a startup, then make a phased plan to get every perspective to 10."
> **Supersedes scoring in:** `GOD_MODE_V10_PERFECT_TEN_ROADMAP.md` (still the source for verified citations).
> **Research folded in:** 2-part Gemini deep-research pass (2026-06-09) — competitor monetization +
> regulatory drivers. Web-sourced, source-URL-per-claim. See §3, §4. One more prompt pending (§7).
>
> **Definition of a real 10:** *one command, one paragraph, or one verifiable external fact closes the
> blocker* — not a box ticked. We do **not** fake traction or stars. Honesty is the spine (see §0).
> **Not everything ships before 2026-06-25 — and that's fine** (Ahmed, 2026-06-09). Phases 0–4 target
> defense; Phase 5 is the post-defense adoption runway.

---

## 0. The honesty spine — three classes of 10

| Class | Meaning | How we reach 10 |
|---|---|---|
| **A — Codeable** | Closed by code / writing / build before defense | Execute the DoD. Most technical + thesis items. |
| **B — Reframable** | Naive metric is capped, but the *lens is wrong* | Replace the wrong frame with the right one, out loud, with evidence. |
| **C — Motion-gated** | Needs real external traction (weeks–months) | Start the *real* motion now; score the honest current number; name the path. **Never fake.** |

**Defense-day thesis statement this plan builds toward:**
> *"Eighteen perspectives are at a provable 10. Two — live traction and founder track record — are
> motion-gated; I started the real motion and can show the curve, not a fake number. Knowing which is
> which is the difference between an engineer and a marketer."*

---

## 1. Market reality (NEW — from research; this reframes everything)

The 2026 AppSec market has **decoupled detection from value**. Verbatim from the research:
> *"Detection is now abundant and low-cost. The new scarce resource — the primary locus of value
> capture — is the ability to definitively verify exploitability, autonomously remediate the flaw,
> and mathematically prove the risk has been eradicated without human intervention."*

**This is ACR-QA's exact thesis.** Consequences:

1. **"Just another SAST tool" is the wrong frame** (and scores a 2 on competition). The right frame:
   ACR-QA sits on the **value frontier** the whole market is racing toward — exploit-verified remediation.
2. **The vanguard doing "re-run the exploit after the patch in CI" is named and ALL closed/paid:**
   ZeroPath (Runtime Validation, post-merge), Aptori ("verify closure"), CodeSentry, Mobb (re-run SAST
   after fix). **ACR-QA is the open-source, $0, first-party-source convergent of this exact paradigm.**
3. **Compliance is THE monetization lever** — every vendor gates SOC2/ISO/EU-CRA/SBOM behind paywalls.
   ACR-QA already has `scripts/generate_evidence_pack.py` + dual attestation → the paid wedge is pre-built.
4. **ACR-QA accidentally built the 2026-compliant feature set as a thesis:** Sigstore/Rekor attestation,
   CRYSTALS-Dilithium3 (= FIPS 204 ML-DSA), CBoM (PQC-aware), SBOM — these are *exactly* the dated 2026
   procurement requirements in §4. The startup story writes itself.

---

## 2. The merged scoreboard (current → target)

### Track T — Thesis / Technical / Product-artifact (mostly Class A → real 10)
| # | Perspective | Now | Target | Phase |
|---|---|:--:|:--:|:--:|
| T1 | Code quality & types | 8.5 | 10 | 2 |
| T2 | Test rigor (coverage + e2e) | 8 | 10 | 2 |
| T3 | Architecture | 9 | 10 | 2 |
| T4 | Focus vs sprawl | 7.5 | 10 | 2 |
| T5 | Security posture (dogfood in CI) | 8 | 10 | 2 |
| T6 | Precision story (external corpus) | 8 | 10 | 1 |
| T7 | Recall story (RealVuln harness) | 8 | 10 | 1 |
| T8 | Novelty / Verified Remediation | 7.5 | 10 | 4 |
| T9 | **Exploit-verify depth (3 live / 13 wired)** | 6.5 | 10 | 1 |
| T10 | Calibration / FPR + ECE | 8 | 10 | 1 |
| T11 | Citation integrity | 9.5 | 10 | 0 |
| T12 | Written thesis | 8 | 10 | 0/4 |
| T13 | Reproducibility | 8.5 | 10 | 1 |
| T14 | Defense readiness | 8.5 | 10 | 4 |
| T15 | Installability (PyPI) | 6 | 10 | 0 |
| T16 | Frontend / UX (dist + deploy) | 7.5 | 10 | 2 |
| T17 | Distribution surface | 8 | 10 | 2 |
| T18 | **Repo hygiene (uncommitted tree)** | 5 | 10 | 0 |
| **T19** | **Robustness / FP-harvest (NEW — item (a))** | — | 9 | 3 |

### Track S — Startup / Venture (research lifted most of these from "reframe" to "defensible")
| # | Perspective | Now | Target | Phase | What the research changed |
|---|---|:--:|:--:|:--:|---|
| S1 | Problem / pain | 7 | 9 | 5 | Market confirms pain is *funded* (detection commoditized, FP fatigue is the buy trigger) |
| S2 | Market / TAM | 8 | **10** | 4 | Now **dated, sourced** regulatory drivers (EU CRA 2026-09-11, etc.) — §4 |
| S3 | Competition | 2 | **8** | 4 | The "open-source + first-party + CI exploit-verify" niche is genuinely **unoccupied** |
| S4 | Differentiation / moat | 3 | **8** | 4 | Precisely nameable: open + first-party + $0 + **PQC-attested compliance evidence** |
| S5 | Business model | 2 | **8** | 4 | Concrete competitor-benchmarked open-core pricing (§3) |
| S6 | GTM / wedge | 4 | 8 | 5 | Compliance-evidence wedge + design-partner motion + leaderboard-inbound |
| S7 | Traction | 1 | honest **4–5** | 5 | Motion-gated. Real curve, not a fake number |
| S8 | Founder / team | 3 | honest **6** | 5 | Reframe "solo grad" → "shipped a full platform solo"; add an advisor |
| S9 | Defensibility (data moat) | 3 | 6 | 5 | Seed `verification_log` flywheel with design partners |
| S10 | Capital efficiency | 8 | 10 | 4 | $0 burn; document unit economics |

---

## 3. ACR-QA's defensible wedge + open-core pricing (designed from competitor data)

**The one-sentence wedge (verified-cite-safe):**
> *Exploit-verified remediation, cryptographically + PQC-attested, for **first-party source code, in CI,
> open-source, at $0** — the one quadrant ZeroPath / Aptori / Mobb (all closed or paid) don't occupy.*

**Open-core pricing, benchmarked against the 13 competitors in the research:**

| Tier | Price | What's included | Competitor anchor |
|---|---|---|---|
| **Free (OSS-forever)** | $0 | Full CLI: 19 engines, exploit-verify, SARIF, local attestation. Free for OSS repos forever | Semgrep/Socket/Mobb/KodeShield all free-for-OSS |
| **Team** | ~$29/dev/mo | Hosted dashboard, scan history, PR merge-gate, Confirmed Tier, SSO-lite | Semgrep $30, Socket $25, Snyk $25, KodeShield $29 |
| **Compliance** | ~$59/dev/mo | **The wedge:** SOC2/ISO/EU-CRA evidence packs, SBOM (CycloneDX 1.6 / SPDX 3.0.1), **dual PQC attestation (FIPS 204)**, audit logs, RBAC | Socket $50, KodeShield $69 gate compliance here |

**Why this is defensible, not delusional:** every competitor monetizes compliance + gates SBOM/SSO; none
ships **open-source + first-party + PQC-attested** evidence. ACR-QA already has the evidence-pack generator
and Dilithium3 signing — the paid tier is *productizing what's built*, not new R&D.

---

## 4. Regulatory tailwinds (NEW — dated + sourced; the TAM engine)

| Driver | Dated trigger | Why it forces a buy | ACR-QA already has |
|---|---|---|---|
| **EU CRA** (Reg. EU 2024/2847) | **2026-09-11**: 24h vuln reporting + machine-readable SBOM; **2027-12-11** full conformity | Global, extraterritorial, market-exclusion penalty | SBOM gen + continuous scan |
| SBOM format mandate | CycloneDX ≥1.6 / SPDX ≥3.0.1, JSON/XML, **SHA-512** hashes | Spreadsheets obsolete; needs tooling | SBOM engine (verify format) |
| **US OMB M-26-05** | **2026-01-23**: decentralized, risk-based; agencies demand SBOM contractually | False Claims Act exposure for false SBOMs | provenance + attestation |
| CISA 2025 Min. Elements | component hash, license, **tool name**, generation context | Defense/Army independent mandates | attestation metadata |
| **SLSA L3 + Sigstore/Rekor** | 2026 procurement baseline; admission controllers reject unsigned | No attestation = artifact rejected | **already does Sigstore Rekor** ✅ |
| **PQC / CNSA 2.0** | FIPS 203/204/205 (2024-08-13); software signing "prefer 2025 → exclusive 2030"; **ML-DSA** | Defense rejects classical-only sigs by 2030 | **already does Dilithium3 = FIPS 204** ✅ |

**Defense slide line:** *"ACR-QA was built as a thesis in 2025–26 and independently implements the exact
2026 procurement stack — Sigstore-attested, FIPS-204-signed, SBOM-emitting, PQC-aware. The regulation
caught up to the design."* (Every date above carries a source URL in the research appendix.)

---

## PHASES (clean, DoD-gated, owner-tagged)

### Phase 0 — Stop the bleeding (≤1 day) · unblocks everything
| # | Item | Owner | DoD |
|---|---|---|---|
| 0.1 | Commit G204 fix + run pre-commit checklist | Claude | ruff+mypy+pytest green; committed |
| 0.2 | Commit thesis chapters + figures (T12/T18) | Ahmed approves | `git status` clean |
| 0.3 | Push to origin/main (T18) | Ahmed | origin == HEAD |
| 0.4 | PyPI publish: wheel ✅ done → OIDC + tag workflow (T15) | Ahmed (3 steps) + Claude (workflow) | `pip install acrqa` from clean venv |
| 0.5 | Number-consistency sweep across all 6 chapters (T11/T12) | Claude | one source-of-truth table; no contradictions |

### Phase 1 — Make the wedge undeniable + fix the FPR story (3–5 days)
| # | Item | Owner | DoD |
|---|---|---|---|
| 1.1 | **Detonate the 7 remaining exploit categories live in Docker (T9)** | Claude | `EXPLOIT_VERIFICATION.md` = 10/10 real runs + logs |
| 1.2 | Extend Verified Remediation to each newly-detonated class | Claude | ≥8 classes: fix proven to kill exploit in-sandbox |
| 1.3 | Compute ACR-QA's **ECE**; cite RuleForge 0.17 as bar (T10) | Claude | ECE number in eval chapter |
| 1.4 | Confirmed Tier = **default** output; `--all` opts into noisy tier (T10) | Claude | clean repo → 0 default false alarms |
| 1.5 | Run OWASP Benchmark Python + RealVuln harness for real; auto-gen figures (T6/T7) | Claude | `make realvuln` / `make owasp` reproduce numbers |
| 1.6 | `make reproduce` runs every headline number (T13) | Claude | stranger reproduces in 2 commands |

### Phase 2 — Close the technical 10s (3–4 days)
| # | Item | Owner | DoD |
|---|---|---|---|
| 2.1 | DATABASE 49%→≥80%, main.py 74%→≥85%, e2e 4→≥12 (T2) | Claude | combined ≥88%; e2e covers critical journeys |
| 2.2 | mypy clean on DATABASE + FRONTEND too (T1) | Claude | `mypy CORE DATABASE FRONTEND` 0 errors |
| 2.3 | Engine facade + ENGINE_MAP in README hero (T4) | Claude | "why 36 engines" in one screen |
| 2.4 | dogfood HIGH=0 wired into CI gate (T5) | Claude | badge proves it |
| 2.5 | Frontend `dist` build + a11y axe pass + deploy (T16) | Claude + Ahmed (deploy) | live URL, Lighthouse ≥90 |
| 2.6 | All 4 distribution channels green (T17) | Ahmed | PyPI + GHCR + Action + VS Code listings live |
| 2.7 | 13th ADR (data-flow contract) + regenerated C4-L3 (T3) | Claude | ADR + diagram in thesis |

### Phase 3 — Robustness & honesty (2–3 days) · contains items (a) and (b)
| # | Item | Owner | DoD |
|---|---|---|---|
| **3.1** | **T19 — Robustness/FP-harvest on a PRE-REGISTERED repo list (item a)** | Claude | list committed *before* scanning; FP/crash log per repo; ≥1 real fix |
| **3.2** | **Test-file gate noise fix (item b — recorded, do after metric review)** | Claude + Ahmed (greenlight) | extend `_TEST_PATH_RE` to default gate; re-baseline FP/precision numbers across thesis |
| 3.3 | Audit broad `except Exception` → narrow/log+re-raise in trust paths (T1) | Claude | no silent swallow on verify path |

**T19 pre-registered repo list, split DEV / HELD-OUT** (principle: *top-downloaded pure-Python PyPI packages
with a test suite, ranked on a fixed date, disjoint from the precision corpus; the split is committed before
any scan and the held-out half is never tuned against — see §7b*):
- **DEV (tune/fix freely, burned for reporting):** `flask`, `click`, `rich`, `pydantic`, `sqlalchemy`,
  `pyjwt`, `paramiko`, `werkzeug`, `pyyaml`, `tornado`
- **HELD-OUT (scan once, never tune, headline number):** `fastapi`, `requests`, `httpx`, `pillow`,
  `starlette`, `redis-py`, `celery`, `pymongo`, `lxml`, `boto3` ⚠️ *httpx already scanned this session —
  it's now DEV-contaminated; swap in a fresh held-out repo before freezing.*
→ commit both halves to `TESTS/evaluation/robustness/PREREGISTERED_REPOS.txt` first; scan `--no-ai`; record
findings + tool crashes per repo. **This is how (b)'s test-noise issue becomes evidence, not anecdote:**
develop the fix on DEV, validate once on HELD-OUT.

### Phase 4 — Startup repositioning (2–3 days, mostly writing) · uses §3 + §4 research
| # | Item | Owner | DoD |
|---|---|---|---|
| 4.1 | `docs/PRICING_POSITIONING.md` → 3-tier open-core model (§3) (S5) | Claude | pricing page w/ competitor anchors |
| 4.2 | Honest market map + unoccupied-quadrant diagram (S3/S4) | Claude | positioning map, verified cites only |
| 4.3 | Regulatory-TAM slide w/ dated drivers + sources (§4) (S2) | Claude | TAM slide, every date sourced |
| 4.4 | Unit-economics one-pager: $0 burn, free-tier ceilings (S10) | Claude | 1-page table |
| 4.5 | Verified Remediation positioned as value-frontier convergence (T8/S4) | Claude | 1 paragraph, ZeroPath/Aptori/Mobb cited |
| 4.6 | Fold all startup Q&A into `docs/QA_PREP.md` incl. "thesis-8 / startup-3, here's why" (T14) | Claude | answers rehearsable |

### Phase 5 — Start the real external motion (ongoing, post-defense OK) · Ahmed-led
| # | Item | Owner | DoD |
|---|---|---|---|
| 5.1 | Demo video → HN + r/netsec + LinkedIn (S6/S7) | Ahmed | posted; a real view/star curve |
| 5.2 | Design-partner outreach to 10 targets (S6/S9) | Ahmed | ≥1 reply; seed verification flywheel |
| 5.3 | Recruit one industry security advisor (S8) | Ahmed | advisor named |
| 5.4 | 3 user interviews (S1) | Ahmed | 3 pain quotes + willingness-to-use signal |
| 5.5 | Funding apps — **GitHub SOSS $10k (rolling, best fit)** + NLnet (2026-08-01) (S7) | Ahmed | ≥1 submitted |
| 5.6 | Become a **CVE Numbering Authority** (Red Hat root) → assign CVEs from ACR-QA findings (S8) | Ahmed | CNA onboarding started |
| 5.7 | Submit ACR-QA to the **RealVuln live leaderboard** (objective third-party rank) (S1/S7) | Claude + Ahmed | result posted on leaderboard |
| 5.8 | Pick one **Big-Four CFP** (NDSS 2026-08-19 / USENIX 2026-08-26 / IEEE S&P 2026-11-10), Tool/SoK track (S8) | Ahmed | abstract drafted |

---

## 6. Sequencing & fallback

**Order:** Phase 0 → 1 → 2 → 3 → 4 (→ 5 ongoing). **If time slips before defense: ship 0 + 1 + 4 + the
defense answers, and defend.** Phase 2/3 are bonus polish; Phase 5 is explicitly post-defense.

---

## 7. Gemini research log — ALL THREE PASSES DONE

**✅ Pass 1+2 (folded into §3/§4):** competitor monetization (13 tools) + regulatory drivers (EU CRA, OMB
M-26-05, CISA, SLSA L3/Sigstore, PQC/CNSA 2.0).

**✅ Pass 3 — non-VC funding / credibility / launch (2026-06-09, folded into Phase 5 + §3.5):**

| Lever | Concrete target | Amount | Deadline | Eligible? |
|---|---|---|---|---|
| **GitHub SOSS Fund** | security micro-grant, rolling | **$10k** | rolling | ✅ solo, GitHub-hosted, OSS, has adoption — **best fit** |
| **NLnet NGI0 Commons/Entrust** | PQC + Sigstore align perfectly | €5k–50k (→€500k) | **2026-08-01** | ✅ global, individuals |
| **Sovereign Tech Fund** | "critical infra" framing | min **€50k** | rolling (~6mo lead) | ✅ global, public-interest |
| **Open Source Pledge** | passive — be a tracked dependency | corp-routed | continuous | ✅ via Open Collective/GH Sponsors |
| **GSoC (as mentor org)** | subsidized student labor to scale | $500/intern + travel | Q1 (UNVERIFIED) | needs active community first |
| **OpenSSF Alpha-Omega** | at scale only; join WGs first | ~$350k avg | proactive (no open call) | aspirational |
| **EU SECURE cascade** | **the loophole** — sell to subsidized EU mSMEs | €30k/mSME | open calls | ❌ direct (non-EU); ✅ as *vendor* to grant-funded EU SMEs |

**Credibility motions (all free):** CVE Numbering Authority via Red Hat root (~4wk onboarding) → assign
CVEs from ACR-QA's own findings = manufactured track record; **RealVuln leaderboard submission** (open
harness, submit via GitHub) = objective third-party rank; **Big-Four CFPs free + ACM 100% OA from 2026-01-01**
— NDSS 2027 abstract **2026-08-19**, USENIX Sec **2026-08-26**, IEEE S&P **2026-11-10** (Tool/SoK tracks fit).

**Launch playbook:** HN "Show HN: An open-source SAST platform with exploit-verified remediation and
FIPS-204 signing" (factual title, repo link, no upvote-begging, no AI replies); r/netsec = vendor-neutral
whitepaper or the Monthly Tool Thread (NOT a product post); Lobste.rs = get invite, 70-day incubation, <25%
self-promo ratio. Full detail saved in [[research-2026-06-funding-launch]].

---

## 7b. Evaluation methodology — the anti-overfitting discipline (answers "we tune every repo we test")

**The risk you named:** scanning a repo → tuning rules until numbers improve → reporting *those* numbers =
**overfitting to the eval corpus**. An examiner asks "did you tune against your benchmark?" and the recall
claim collapses. **Tuning is fine; tuning-then-reporting-the-same-repo is not.**

**The discipline (now mandatory for every benchmark in this project):**
1. **DEV set** — inspect, tune, fix freely. The moment a repo is tuned against, it is DEV *forever*. Burned for reporting.
2. **HELD-OUT set** — pre-registered + committed **before** scanning, **never** tuned against, scanned **once**.
   Headline numbers come ONLY from here.
3. **Report both**; lead with held-out. The DEV↔held-out gap is itself an honesty signal.
4. Already done right in: X1 live-CVE blind holdout, LLM-detector 16-repo held-out (+5.2pp). Make it global.

→ This governs T19 (Phase 3.1): its 20-repo list is split DEV/HELD-OUT *before* any scan; the test-gate fix
(3.2) is developed on DEV and validated once on held-out.

---

## 8. Guardrails (unchanged discipline)

1. No item ships without DoD met + tests green + pre-commit checklist passed.
2. No faked Class-C number. Traction/founder/moat get **honest** scores + a named motion.
3. Every Gemini claim is web-cross-checked before it enters the thesis or a public page.
4. Item (b) — the test-gate fix — **changes thesis-load-bearing metrics**, so it waits for Ahmed's
   explicit greenlight + a full re-baseline (Phase 3.2). Recorded so we don't forget.
5. T19's repo list is **pre-registered** (committed before scanning) so results are evidence, not cherry-picking.
6. **Hold-out discipline (§7b) is mandatory:** any repo tuned against is DEV forever; headline numbers come
   only from a never-tuned held-out set. "We enhanced after testing" is fine on DEV, fatal if reported.

---

## 9. What "done" looks like

| Floor (pass) | Target | Stretch |
|---|---|---|
| Track T all ≥9; clean repo; PyPI live; defense answers rehearsed | Track T all 10; 10/10 detonation + ECE | + Zenodo DOI + live deploy URL |
| Startup story (S2/S3/S4/S5) defensible w/ sourced research | Pricing + market map + TAM slide | + 1 design-partner reply |
| Defense graded A | A+ | A+ w/ commendation |

*Created 2026-06-09. Research-grounded. Execution starts at Phase 0. The honest-ceiling perspectives
(S7/S8/S9) are features of the analysis, not bugs in the plan.*
