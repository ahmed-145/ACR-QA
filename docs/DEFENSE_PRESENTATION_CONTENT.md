# ACR-QA — Defense Presentation Content (GP2, June 2026)

**Format:** 10–15 min talk + 5 min live demo. ~12 content slides + title + outline + Q&A.
**Goal:** lead with the problem, prove it works with real numbers, show it live, end strong.

> **Build note:** Your old deck (`Graduation Project - Presentation (9).odp`) was the GP1 (Fall 2025)
> version. It's missing your strongest GP2 evidence (Confirmed Tier, exploit verification, evaluation
> results) and has two **stale claims to fix**: "42–68% fewer hallucinations" and "JS/Java coming"
> (JS/Go adapters now exist). Use the numbers in this doc — they match the thesis.

---

## Recommended outline (slide order)

1. Title
2. Introduction (context)
3. Problem Statement
4. Motivation & Core Innovations
5. System Architecture
6. RAG Explanation Engine  ← **keep, but tighten** (see note)
7. Data Model  ← **compress to half a slide or merge into Architecture** (see note)
8. **Evaluation & Results ⭐ NEW — your most important slide**
9. **Live Demo ⭐ (5 min)**
10. Implementation Status
11. Conclusion & Future Work
12. Questions

**On the RAG slide:** keep it — RAG grounding is a genuine core innovation and committees love a
clear technical mechanism. Just don't let it run long; one diagram + the "we hand the AI the rulebook
before it answers" line is enough. **On Data Model:** it's the weakest standalone slide for a defense
(committees rarely grill schema). Compress it to a few bullets or fold the "every decision is logged →
full audit trail" point into Architecture, and give the reclaimed time to Evaluation.

---

## ⭐ Slide 8 — EVALUATION & RESULTS (the new must-have)

**Headline:** *Not just built — measured, on adversarial corpora, against the standard tools.*

**Layout: a results table + 2–3 proof points.**

| What we measured | Result |
|---|---|
| **Confirmed-Tier precision** (auto-block stratum) | **96.4%** (95% CI 90.9–100%) |
| **CVE recall** (pre-registered battery) | **100% — 8/8 detectable** |
| **Head-to-head F₁** | **ACR-QA 98.2%** vs Semgrep 45.7% vs Bandit 21.8% |
| **OWASP Top 10 coverage** | **9 / 10 categories** |
| **Test suite / coverage** | **3,017 tests · 88% CORE coverage** |
| **RealVuln 2026 leaderboard** | **25.1%** — beats Semgrep 17.5%, Snyk 17.4%, SonarQube 6.5% |

**Three things to say out loud (this is what wins a defense):**

1. **"We separated detection from trust."** Most tools dump 30–70% false positives. ACR-QA adds a
   *Confirmed Tier*: a 4-gate stratum (HIGH severity + 22-rule curated set + production-code path +
   external Bandit HIGH-confidence) that hits **96.4% precision** — high enough to **auto-block a merge**.

2. **"We don't just claim a vulnerability — we detonate it."** For confirmed findings, ACR-QA fires a
   real exploit payload in an ephemeral Docker sandbox: SQLi `' OR 1=1`, SSTI `{{7*7}}→49`,
   command injection. Verdict is `verified-exploitable` / `verified-unexploitable` / `unverified`.
   **Verified live: SQLi + SSTI detonate, safe code correctly does not** (no false detonation), and the
   full detect → exploit → patch → re-exploit pipeline passes.

3. **"Every result is signed."** Each scan is ECDSA-P256 signed, logged to Sigstore Rekor, with
   SLSA L3 provenance — a tamper-evident audit trail an auditor can verify in one command.

**Pre-empt the committee's #1 question — "did you overfit / are these numbers real?":**
Two corpora (intentionally-vulnerable apps + 30 production libraries), pre-registered methodology,
Wilson confidence intervals, and the RealVuln *independent* leaderboard. The Bandit confidence gate is
an *external* signal — so the Confirmed Tier is **not** scored against our own labels (non-tautological).

---

## ⭐ Slide 9 — LIVE DEMO (5 minutes)

**On-screen title only** (e.g. "Live Demo — ACR-QA in action"). The slide is a placeholder; the screen
switches to the dashboard. **Demo script below.**

### Before you walk in (de-risk)
```bash
make seed-demo          # pre-loads 3 real scans: payments-api, web-backend, internal-tools
make api                # or: .venv/bin/uvicorn FRONTEND.api.main:app --port 8000
```
Open `http://localhost:8000` and confirm the Overview shows real numbers. **This is your safety net** —
if anything fails live, you still have a populated dashboard to walk through.

### The 5-minute flow
1. **Overview (45s)** — "Here's the fleet: 3 apps scanned. Note the **Confirmed Tier** tile — these are
   the findings we'd auto-block on, at 96.4% precision. The green Trust Layer banner shows the live KPIs."
2. **Run a fresh scan (90s)** — trigger a scan on a small app so they see it work end-to-end
   (~60–90s). "Detection tools run in parallel, normalize to one schema, then the trust gates apply."
3. **Open a confirmed finding (90s)** — show a real SQL-injection: the code, the canonical rule, the
   **RAG explanation citing the rule**, and the **exploit-verification result** (the payload that fired).
   "This is the difference — not 'maybe a bug', but 'we proved it's exploitable'."
4. **OWASP heatmap + attestation (45s)** — show the real OWASP coverage on the run, and the signed
   attestation. "Every scan is cryptographically signed."

### Which repo to scan LIVE
- **Live fresh scan → `payments-api`** (the `comprehensive-issues` sample). Richest findings
  (SQLi, hardcoded secrets, md5 crypto, 13 HIGH, 4 Confirmed-Tier), still scans in ~60–90s.
- Keep `web-backend` and `internal-tools` pre-seeded so the dashboard fleet looks populated.
- **Fallback:** if the live scan is slow/flaky on the projector network, just walk the *pre-seeded*
  `payments-api` run — same story, zero risk.

### Use the fleet you already have (strong material)
The dashboard already holds scans of **real, recognizable open-source projects** from your benchmark
runs — `react`, `webpack`, `psf/requests`, `encode/httpx`, `tiangolo/fastapi`, `pallets/flask`. **Lead
with these**: "ACR-QA scanned real production libraries the committee knows." It's far more credible than
sample apps alone. Two power moves:
- **Famous-repo credibility:** open `psf/requests` or `tiangolo/fastapi` — "this is the actual FastAPI
  source; here's what ACR-QA found and how it prioritized it."
- **Zero-false-positive proof (X6):** the fleet also holds mature packages with **0 HIGH findings**
  (`numpy`, `pandas`, `pydantic`, `anyio`, `attrs`…). That's the point: "On clean, mature code ACR-QA
  stays quiet — **0.0% HIGH false-positive rate**. It doesn't cry wolf." This directly answers the
  committee's false-positive question with live evidence.

So the honest framing tier-list for the demo: **famous real repos** (credibility) → **clean demo apps
with planted vulns** (to show the exploit-verification detail clearly) → **mature 0-FP packages**
(to prove low noise).

> **Are these real repos?** Yes — real, intentionally-vulnerable sample applications (the same kind
> used in security courses). The detection, exploitation, and signing are all genuine. If asked, say
> exactly that: "These are deliberately-vulnerable sample apps; the tool's analysis of them is real."

---

## Number corrections vs the old deck (fix before presenting)

| Old deck said | Use instead |
|---|---|
| "42–68% fewer hallucinations" | Keep only if your thesis still backs it; otherwise lead with the **entropy filter rejects 96% of hallucinated responses** figure from the thesis. |
| "JS/Java plugins coming" | "Python, **JavaScript/TypeScript, and Go adapters implemented**; PHP/Java via Semgrep generic rules." |
| "6+ tools" | "**Nineteen analysis engines** across detection, scoring, RAG, reachability, taint, and attestation." |
| (no eval numbers) | Add the Evaluation table above. |
| "CSE493 – Graduation Project 1 / Fall 2025" | "CSE494 – Graduation Project 2 / 2026" |

---

## Closing line (Conclusion slide)

> "ACR-QA makes high-quality, multi-tool security analysis — with AI explanations you can trust and
> exploit-proof you can verify — available to any team, on any machine, at zero cost. 96.4% precision,
> 100% CVE recall, every result signed. Thank you."
