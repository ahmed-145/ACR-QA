# ACR-QA God Mode Plan v8 — Perfect Score (10/10 on Every Aspect & Perspective)

> **Created:** 2026-06-02
> **Author:** Ahmed Mahmoud Abbas
> **Trigger:** A 20-perspective rating exercise. The project scores 8–9 on academic/portfolio
> perspectives but 4–6 on business/community/research-rigor perspectives. This plan closes *every*
> gap to a defensible 10 — and is brutally honest about which 10s are code-achievable now versus
> which are gated on real users, time, or external validation no solo fresh-grad can fake.
>
> **Companion docs:** `GOD_MODE_V7_COMPETE_PLAN.md` (the competitive tracks A–H this plan executes),
> `ACTIVE_ROADMAP.md` (the free execution list), `GOD_MODE_V6_BUSINESS_PLAN.md` (positioning).
>
> **The honest framing:** A 10 from a thesis examiner is *earned with code and rigor*. A 10 from a
> VC is *earned with traction you cannot manufacture in 23 days*. This plan separates the two. It
> drives every **code/rigor-gated** perspective to a real 10 before defense, and lays the **shortest
> honest runway** to the people/time-gated 10s after.

---

## 0. THE 11/10 CUT — read this section if you read nothing else

> **Added 2026-06-03.** If §1–§6 below are the *menu* (20 perspectives, 6 tracks, ~35 items), this
> section is the *order*. It exists because the rest of this plan is maximalist, and the project's own
> diagnosed weakness is **sprawl** (perspectives #7, #15, #17 all flag it). Executing all 35 items at
> 70% quality produces an 8/10 spread thin. **11/10 is the opposite discipline.**

### What 11/10 actually means

A 10/10 is "every box checked." **An 11/10 is "two or three things so good they're undeniable,
wrapped in zero embarrassing gaps."** Nobody remembers the project with a green uptime badge. They
remember the one that did something *no competitor can do* and proved it on *neutral ground*. So:

> **11/10 = (a memorable, uncontestable capability) × (a number the skeptic can't dismiss) ÷ (zero
> stupid gaps).** Maximize the numerator with depth; drive the denominator to zero with hygiene;
> ignore everything that doesn't move either.

### The 3 pillars (the entire numerator)

| Pillar | The move | Why it's an **11**, not a 10 | The *exceptional* bar (what makes it memorable, not just "done") |
|---|---|---|---|
| **P1 — Verified Remediation** | Detect → exploit-fires → AI fix → **re-run the exact exploit** → confirm it now fails → sign `(vuln_proof, fix_diff, fix_proof)` to Rekor (Track C1–C2) | The entire industry retests fixes *statically* (Snyk "80% accuracy"). **Nobody re-runs the actual exploit.** This is the one sentence that makes a security researcher stop scrolling. | A live demo: exploit working on screen → AI patch applied → same exploit now failing → "verify this chain on Rekor" button resolves. End-to-end, one command, in the defense room. |
| **P2 — OWASP Benchmark score** | Run OWASP Benchmark for Python; publish the official scorecard with MCC + CIs (Track A1, A2) | Every number so far is on *our* corpus (SecurityEval). OWASP is **neutral ground the field already cites.** It converts "they benchmarked themselves" into "they beat the standard." | Published `OWASP_BENCHMARK.md` with the official Youden-index scorecard, pre-registered methodology, and an honest line if any category loses. Reproducible in 2 commands. |
| **P3 — The 91% recall, on the record, honestly** | Already shipped: 91.0% detectable-CWE recall, P-1 retracted, RECONCILIATION.md (Tracks done today) | A *win on detection* with a *public retraction of our own flawed benchmark* is the rarest thing in this space: a number that goes up **and** integrity that can't be impeached. | ✅ DONE. The 11-move remaining is to *say it out loud in defense*: "we found our own benchmark was wrong, fixed it, published both." |

### The denominator — zero embarrassing gaps (hygiene, do first, cheap)

These don't win anything; leaving them broken *loses* everything. An examiner who runs `--version` and
sees `v3.2.5` on a "v5" thesis discounts every other claim.

- **Version sync** (5 strings disagree; `--version` prints v3.2.5) → one source of truth + regression test.
- **Docs all say one number** (✅ done today — synced to 91.0%).
- **Green gate** (ruff + mypy + full pytest) on every commit (✅ holding).

### What 11/10 is explicitly NOT (defer all of this to post-defense)

The following are real and in §2 below, but they are **denominator-polish with diminishing returns** —
each moves one perspective 8→10 and changes neither the grade nor the differentiation:

> UptimeRobot/status page (G1) · VPAT-lite a11y (G3) · load-test refresh (G4) · Zenodo DOI (E3) ·
> hosted live-scan demo (E2) · engine-consolidation refactor (R1–R3) · multi-language exploit (B2) ·
> LLM-jury (B4).

Pulling these forward is how you turn a focused 11 back into a sprawling 8. **Resist it.**

### The sequence (and nothing else until each is at the exceptional bar)

1. **Version sync** — hours. Removes the one gap that taxes every other claim.
2. **OWASP Benchmark (P2)** — days. The neutral-ground number that silences the skeptic.
3. **Verified Remediation (P1)** — ~1–2 weeks. The uncontestable moat; the demo that wins the room.
4. **Rehearse the honesty narrative (P3)** — the reconciliation + retraction, memorized cold.

When these four are done *to the exceptional bar above*, the project is an 11/10 — and not one minute
was spent on a status badge. Everything in §1–§6 that isn't one of these is a post-defense backlog.

---

## 0.1 Ground Truth — what the repo actually looks like today (refreshed 2026-06-03)

Audited the live tree. Plan is built on these *facts*, not the docs' claims:

| Finding | State | Severity |
|---|---|---|
| **Version strings disagree 5 ways** | `pyproject=5.0.0rc1`, `CORE/__init__=5.0.0b1`, `main.py` has `v4.6.0`, `v3.6.0`, AND `v3.2.5`; `--version` prints **v3.2.5** | 🔴 The one remaining hygiene gap — fix first |
| **Recall 91.0% — committed & published** | 23 taint/gap-closing Semgrep rules shipped (86 total); P-2 = 81/89 detectable; all docs synced | ✅ Was the 🟠 risk; now resolved (commits f13aab6, 74cae8c, 91c6b52) |
| **P-1 retracted, RECONCILIATION.md published** | Honest methodology write-up; pre-registration committed before runs | ✅ The integrity 11-move, banked |
| **Exploit verifier covers 4 categories** | `sql-injection`, `command-injection`, `ssti`, `path-traversal` | 🟡 Pillar P1 will extend the *fix-loop*, not necessarily the category count |
| **OWASP Benchmark never run** | corpus not cloned; zero results | 🟡 **Pillar P2 — the single biggest rigor gap** |
| **Verified Remediation absent** | no `fix_verified`, no re-exploit loop in `CORE/` | 🟡 **Pillar P1 — the frontier, not started** |
| **Tests green** | 2,725 passing, mypy clean | 🟢 |

**Implication:** the denominator is one fix away from zero (version sync). The numerator is two builds
(OWASP score + Verified Remediation). That is the whole 11/10 — three moves, not thirty-five.

---

## 1. The Scoreboard — every perspective, its blocker, its 10-move

20 perspectives from the rating. Each row: current score → the *one thing* blocking 10 → the move.

### Tier A — Code/Rigor-gated (achievable to a real 10 before defense)

| # | Perspective | Now | Blocker to 10 | 10-Move | Track |
|---|---|:---:|---|---|---|
| 1 | Thesis examiner | 9.5 | Version bug; one demo unfilmed | Fix versions, film demo | F1, H |
| 2 | External examiner (skeptic) | 7.5 | "64 vs 96" still answerable as gotcha | OWASP + CWE-matching + memorized reconciliation | A1–A4 |
| 3 | CS researcher / reviewer | 6.5 | Not on standard corpora; no published artifact | OWASP Benchmark score + Zenodo DOI replication pkg | A1, E |
| 4 | Statistician | 6.0 | Small n, overlapping CIs | Power to n>200 (OWASP+SecurityEval+CVE); report MCC everywhere | A5, A2 |
| 5 | Hiring mgr (backend) | 9.0 | Already strong; sprawl optics | One-page architecture diagram + "why 40 engines" note | C-doc |
| 6 | Hiring mgr (security) | 8.0 | Exploit set narrow | Expand to 10+ exploit categories | B1 |
| 7 | Staff engineer | 7.0 | 40+ engines = sprawl smell | Engine consolidation map + dead-code audit | C-refactor |
| 8 | SRE / DevOps | 8.0 | No live SLO/uptime proof | UptimeRobot + public status page + load-test refresh | G |
| 9 | AppSec buyer (CISO) | 6.0 | No case studies, prod-trust | Design-partner pilot + signed evidence pack demo | B-people |
| 10 | Competitor | 7.0 | Recall/rule-count dismissable | Publish 78.7% recall win + Verified Remediation | A, C |
| 11 | Developer (daily user) | 6.5 | Scan latency, Docker friction | Sub-30s confirmed-only fast path; daemonless verify option | G2 |
| 12 | Landing-page visitor | 8.0 | Static, no live "try it" | Hosted live-scan demo (paste code → confirmed findings) | E2 |
| 13 | Auditor (SOC2/ISO) | 8.5 | Evidence pack not end-to-end demoed | One-command full chain: scan→exploit→sign→Rekor→pack | C2, G |
| 14 | Accessibility user | 8.0 | No audited a11y report | axe-core CI gate + published VPAT-lite | G3 |
| 15 | Future-you (1yr) | 7.0 | Over-engineering regret | Consolidation + "lessons" retro doc | C-refactor |
| 16 | Honesty police | 9.0 | Already high | Publish the unflattering OWASP number too | A6 |
| 17 | Maintainability | 6.5 | Bus-factor 1, sprawl | Module ownership map + CONTRIBUTING depth + architecture ADRs | C-doc |
| 18 | "Is it cooked?" risk | 7.0 | Two metrics too close in README | Restructure README: recall-headline, precision-as-instrument | A6, F |

### Tier B — People/Time-gated (honest ceiling pre-defense; real 10 is post-defense)

| # | Perspective | Now | Pre-defense ceiling | The only real path to 10 | When |
|---|---|:---:|:---:|---|---|
| 19 | VC | 4.0 | **7** (great tech, credible benchmarks, 1 design partner) | Real revenue + retention + a team. Cannot be faked. | 6–18 mo post |
| 20 | OSS maintainer / community | 5.0 | **7** (clean repo, good-first-issues, real CHANGELOG) | External contributors + stars + cited spec. Time + launch. | 3–12 mo post |

> **The honest line for defense:** "Perspectives 1–18 are at 10. Perspectives 19–20 require traction
> that takes months of real-world adoption — here is the runway, and here is why a thesis is graded on
> 1–18, not on a Series A." Saying this *out loud* in the defense is itself a 10-move: it shows you
> understand the difference between a thesis and a company.

---

## 2. Execution Tracks — what to actually build, in order

Each item has a **Definition of Done (DoD)**. No item is "done" without its DoD met and tests green.

### TRACK 0 — Credibility Fixes (the denominator → zero embarrassing gaps) 🔴

- **0.1 — Version sync.** ⬅️ **ONLY ITEM LEFT — do first.** Make `pyproject.toml`, `CORE/__init__.py`,
  and all of `CORE/main.py` (currently `v4.6.0`/`v3.6.0`/`v3.2.5`) read one string from a single source
  (`CORE.__version__`). Add `test_version_sync.py` asserting they match.
  **DoD:** `python CORE/main.py --version` prints `5.0.0rc1`; regression test passes.
- **0.2 — Commit & publish the recall win.** ✅ **DONE (2026-06-03).** Not 78.7% — pushed to **91.0%**.
  23 new Semgrep rules shipped (86 total), P-2 = 81/89 detectable, every doc synced, RULE_MAPPING +
  RULE_SEVERITY + tests added. Commits f13aab6, 74cae8c, 91c6b52.
- **0.3 — Green gate.** ✅ **HOLDING.** 2,725 passing, mypy clean, ruff clean on every commit.

### TRACK A — Benchmark Credibility → silences external examiner, researcher, statistician

- **A1 — Run OWASP Benchmark for Python.** Clone the corpus, run `scripts/run_owasp_benchmark.py`,
  produce the official scorecard (TP/FP/TN/FN, Youden index). This is THE benchmark buyers/examiners
  recognize. **DoD:** `docs/evaluation/OWASP_BENCHMARK.md` with scorecard + reproduce commands.
- **A2 — MCC everywhere.** Report Matthews Correlation Coefficient alongside P/R/F1 on every corpus
  (already in `run_benchmark_p2.py` — propagate to all benchmark docs). **DoD:** MCC column in every
  results table.
- **A3 — CWE-level matching.** A finding is TP only if its canonical rule's CWE matches the labeled
  CWE. **DoD:** P-1/P-2 re-run with CWE matching; numbers move, documented honestly.
- **A4 — Manual triage of every Confirmed finding.** Hand-verify real/exploitable for each. If 12/14
  are genuinely real, true precision ≈ 90% and the file-level 64% *understates*. **DoD:** triaged
  ground-truth table in `RECONCILIATION.md`.
- **A5 — Power the sample to n>200.** OWASP (~2,700 Python cases) + full SecurityEval (Copilot+InCoder+
  Insecure) + CVE battery. **DoD:** every headline stat has CI narrower than ±10pp.
- **A6 — Pre-register + publish the unflattering.** Methodology committed before each run; report
  losses. Restructure README so recall (78.7%, a win) leads and 96.4% is framed as a precision
  *instrument*, never a bare stat next to recall. **DoD:** README passes the "one-skeptic-question" test.

### TRACK B — Widen the Exploit Moat → security hiring mgr, competitor

- **B1 — Expand exploit categories from 4 → 10+.** Add to `exploit_verifier.py` `RULE_TO_CATEGORY` +
  `PAYLOADS` + sandbox harness: SSRF, XXE, insecure deserialization (pickle/yaml RCE), open redirect,
  auth-token leakage, ReDoS, LDAP injection. Each with a safe observable PoC. **DoD:** ≥10 categories,
  each a passing exploit test.
- **B2 — Multi-language exploit verification.** Extend sandbox to JS/Express + Go/net-http. **DoD:**
  one JS + one Go exploit verified end-to-end.
- **B3 — Reachability score (0–100).** Fuse taint + call-graph + dependency reachability into one
  number; gate Confirmed Tier on `score≥threshold OR exploit-verified`. **DoD:** score on every
  finding; documented.
- **B4 — LLM-jury for non-exploitable classes.** Crypto/logic/config findings get a calibrated
  multi-model jury verdict + cited rationale. **DoD:** every finding has DAST verdict OR jury verdict.
- **B5 — Calibrated confidence + ECE<0.1.** Ship a probability with a reliability diagram, not a bare
  tier. **DoD:** ECE<0.1 reported on held-out corpus — a genuine research contribution.

### TRACK C — Verified Remediation (the frontier nobody else has) → competitor, auditor, researcher

This is the single most differentiating thing left to build. **Nobody re-runs the exploit after the fix.**

- **C1 — Verified-fix loop.** Pipeline: detect → exploit-verify (fires) → autofix patch → apply in
  sandbox → **re-run the exact exploit** → confirm it now fails → `fix_verified=true`. **DoD:** ≥3 vuln
  classes where a generated fix is *proven* to close the exploit in-sandbox.
- **C2 — Attested remediation chain.** Sign `(vuln_proof, fix_diff, fix_proof)` as one ECDSA + Rekor
  record. Auditor replays: exploit working → patch → exploit failing, cryptographically chained.
  **DoD:** signed remediation bundle in Verified Finding **v2** schema.
- **C3 — Fix-quality gate.** Reject fixes that don't close the exploit, break tests, or add a finding.
  **DoD:** 0 regressions in the verified-fix corpus.
- **C4 — Verified MTTR.** Track time-to-a-fix-proven-to-close-the-exploit. **DoD:** published verified-MTTR.

### TRACK refactor — Kill the Sprawl Smell → staff engineer, maintainability, future-you

- **R1 — Engine consolidation map.** Audit all ~40 `CORE/engines/*`. Classify: core / experimental /
  dead. Document which are pipeline-critical vs eval-only. **DoD:** `docs/architecture/ENGINE_MAP.md`
  with a one-line purpose + status per engine.
- **R2 — Dead-code + coverage audit.** Vulture + coverage on `CORE/`. Remove or quarantine truly-dead
  paths. **DoD:** no 0%-coverage engine in the default pipeline without a documented reason.
- **R3 — Module ownership + ADR backfill.** Every major subsystem gets an ADR explaining *why*.
  **DoD:** ADR per engine cluster; CONTRIBUTING points a new dev to the right file in <5 min.

### TRACK G — Ops & UX Proof → SRE, daily developer, a11y, auditor

- **G1 — Live status page + UptimeRobot.** Public uptime proof. **DoD:** status.acrqa.* green badge.
- **G2 — Sub-30s confirmed-only fast path.** A `--fast` mode that skips full-output engines and the
  Docker sandbox warmup, returning Confirmed Tier in <30s. **DoD:** measured <30s on comprehensive-issues.
- **G3 — a11y CI gate.** axe-core in Playwright; publish a VPAT-lite. **DoD:** axe gate green; report in docs.
- **G4 — Load-test refresh.** Re-run k6/locust, publish p95/RPS. **DoD:** `LOAD_TEST_RESULTS.md` current.

### TRACK E — Own the Benchmark + Public Artifact → researcher, OSS, honesty

- **E1 — Verified Finding v2 spec** (adds remediation chain from C2). **DoD:** schema + one example bundle.
- **E2 — Hosted live-scan demo** (paste code → Confirmed findings, in-browser). **DoD:** public URL.
- **E3 — Zenodo replication package + DOI.** Code + corpora pointers + scripts + results, citable.
  **DoD:** DOI minted; README cites it.

### TRACK F/H — Defense Polish (human-gated, Ahmed-led)

- **F1** Film 5-min demo (OBS) → YouTube. **F2** Dry-run with Dr. Samy. **H1** Memorize the
  reconciliation answer cold. **H2** Update QA_PREP with the OWASP + 78.7% + Verified Remediation Q&As.

---

## 3. Sequencing — the order that maximizes defense-readiness

| Phase | Window | Items | Why this order |
|---|---|---|---|
| **P0 — Today** | hours | 0.1, 0.2, 0.3 | Free credibility. Version + publish 78.7% + green gate. |
| **P1 — This week** | 3–4 days | A1, A2, A3, A6 | OWASP score + MCC + CWE-matching kills the #1 defense risk. |
| **P2 — Week 2** | 5 days | B1, C1, C2 | Exploit breadth + Verified Remediation = the uncontestable moat. |
| **P3 — Week 2–3** | 4 days | A4, A5, B5, R1 | Triage table, power the sample, calibration, sprawl map. |
| **P4 — Week 3** | 3 days | E1, E2, E3, G1–G4 | Public artifacts + ops proof. |
| **P5 — Pre-defense** | 2 days | F1, F2, H1, H2 | Demo, dry-run, memorize answers. |
| **Post-defense** | months | VC/OSS runway (§4), B2–B4, C3–C4, R2–R3 | The 10s that need real users + time. |

> **Hard rule (from ACTIVE_ROADMAP):** Defense day is a milestone, not a deadline. If P2/P3 slip,
> ship P0+P1+P5 and defend — that alone moves 8 of the 18 code-gated perspectives to 10.

---

## 4. The Honest Runway to the Two People-Gated 10s

These cannot be coded into existence. Stating the real path *is* the mature move.

**VC → 10 (6–18 months):** 1 design partner using it on a real repo (in progress, `DESIGN_PARTNER_
OUTREACH.md`) → 3 paying pilots → retention data → a co-founder/team. The tech is already ahead of
the market; the gap is *commercial proof*, which is a function of calendar time and sales, not code.

**OSS community → 10 (3–12 months):** Post-defense HN/r/netsec launch (copy ready in
`LAUNCH_POSTS.md`) → good-first-issues + responsive maintenance → first external PR → first external
tool citing the Verified Finding spec. An empty Discord is worse than none; community is *earned after*
the launch, not before.

**What to do now for both:** make the repo *contributor-ready* and *buyer-ready* (R3 ownership map,
E1–E3 public artifacts, G1 status page) so that when traction comes, nothing technical blocks it.

---

## 5. Definition of "Perfect Score" for this plan

This plan succeeds when, **by defense day**:

| Floor (passing) | Target | Stretch |
|---|---|---|
| Versions synced, 78.7% published, gate green | + OWASP score published | + MCC on every corpus |
| External-examiner risk neutralized (A1–A6) | + Verified Remediation demo (C1–C2) | + ECE<0.1 calibration |
| 8/18 code-gated perspectives at 10 | 14/18 at 10 | 18/18 at 10 |
| Demo filmed, reconciliation memorized | + Zenodo DOI | + hosted live demo |
| Honest VC/OSS runway *stated* in defense | + 1 active design partner | + first external contributor |

**The one sentence:** *Make all 18 code/rigor perspectives a real 10 before defense; lay the shortest
honest runway to the 2 traction perspectives; and turn the act of distinguishing the two into the
single most credible thing you say in the defense room.*

---

## 6. Anti-Scope-Creep Guardrails (carried from ACTIVE_ROADMAP)

1. **No item without a DoD met + tests green.** No half-shipped tracks.
2. **P0 before anything.** The free credibility fixes are non-negotiable and come first.
3. **Honesty over headline.** Every benchmark methodology committed before the run; publish losses.
4. **Defense is a waypoint.** Post-defense items stay post-defense. Don't panic-pull Track C forward
   if P0+P1 aren't rock-solid.
5. **Don't fake the people-gated 10s.** No vanity metrics, no empty Discord, no "users" who are you.

---

*Plan v8 created 2026-06-02. Supersedes nothing — it executes the open tracks of
`GOD_MODE_V7_COMPETE_PLAN.md` against a concrete, perspective-by-perspective scoreboard.*
