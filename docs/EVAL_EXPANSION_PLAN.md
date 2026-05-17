# Evaluation Bulletproofing Plan

**Status:** COMPLETE ✅ 2026-05-17 · **Target:** v4.6.0
**Companion to:** `UI_PHASE_3_PLAN.md`, `UI_TESTING_PLAN.md`
**Replaces:** the original 8h "4-repo corpus expansion" plan (kept as Tier 3 below)

---

## Mission

Close the **one** thesis-defense critique that actually has teeth: *"Your benchmarks are toy apps; how do I know this works on real production code?"*

The verbal defense alone (in `PRESENTATION_SCRIPT.md`) buys time but doesn't fix the underlying weakness: **10 of 12 current eval repos are intentionally vulnerable, and the 2 real ones (Flask, httpx) are author-triaged — graded-your-own-homework risk.**

This plan adds **external ground truth** and **independent validation** so the eval section survives a sharp examiner who pushes past the verbal pivot.

## The Critique We're Addressing

> *"97.1% precision sounds great, but your benchmark set is four intentionally vulnerable Python toy applications (DVPWA, Pygoat, VulPy, DSVW). These are designed to be found. A real evaluator will ask: what happens on a real production codebase? You acknowledge this in your limitations section, but it's the part a sharp examiner will push on hardest."*

Current corpus reality check:

| Repo | Type | Ground truth source | Critique vulnerability |
|---|---|---|---|
| DVPWA, Pygoat, VulPy, DSVW, vulnerable-flask-app | **Toy** | Author-labeled | "Designed to be found" |
| NodeGoat, DVNA, DVWS-Node, Juice Shop | **Educational** | Author-labeled | "Designed to be found" |
| bandit-test-cases | **Test fixtures** | Tool-author labeled | "Tests for the test" |
| Flask, httpx | **Real** | **Author-triaged FP only** | **"Graded your own homework"** |

**10/12 are toy. 2/12 are real but self-labeled. The defense is brittle.**

---

## The 4 Tiers

### TIER 0 — Integrity Infrastructure (3h, Run Before Anything Else)

The cheapest insurance in the plan. Without it, every number in subsequent tiers is only as
trustworthy as whoever typed it in. Tier 0 forces honesty by making cheating mechanically
impossible: pre-registration prevents cherry-picking, automated audit prevents stale numbers,
reproducibility prevents "trust me bro" claims.

#### The four ways to fool yourself (without Tier 0)

| Risk | Without Tier 0 | With Tier 0 |
|---|---|---|
| Cherry-pick CVEs you know you'll catch | Easy — drop misses silently | Blocked — YAML committed before scan |
| Move goalposts on "close enough" detections | Tempting on the 14th CVE at 2am | Blocked — strict ±3-line scoring rule in code |
| Stale numbers in EVALUATION.md | Inevitable as code evolves | Blocked — CI fails if doc disagrees with data |
| Silent skips of hard CVEs | "I'll come back to that" → never does | Blocked — skipped CVEs documented with reason |

#### Deliverables

1. **`docs/evaluation/INTEGRITY.md`** — the charter:
   - Pre-registration commitment ("YAML committed before scan")
   - Strict scoring rule: detected = HIGH severity finding within ±3 lines of vulnerable line
   - Skipped-CVE log (every CVE we excluded gets a reason)
   - Adversarial review checklist (questions I'll ask of every claim)
   - "Things I tried to disprove and couldn't" section

2. **`scripts/audit_eval_numbers.py`** — the enforcer:
   - Walks `EVALUATION.md` for every percentage / count claim
   - Re-derives each from source data (CVE YAMLs, scan outputs, ground-truth files)
   - Fails CI if any number in the doc doesn't match the source
   - Output: green ✓ per verified claim, red ✗ for drift, with file:line

3. **`make eval-reproduce`** — the one-command full re-run:
   - Clones all eval repos at pinned commit SHAs
   - Runs ACR-QA against each
   - Generates fresh numbers
   - Diffs against checked-in `EVALUATION.md`
   - Exits non-zero if numbers drift beyond rounding tolerance

4. **Adversarial review pass #1** — first audit of current numbers:
   - Run `audit_eval_numbers.py` against current `EVALUATION.md`
   - Document every claim that fails the audit
   - Either fix the claim or document why the source is correct

#### Why this is non-negotiable

A supervisor who sees `make eval-reproduce` and `audit_eval_numbers.py` cannot push back on data integrity. Without these, every number is "trust me." With them, every number is *checkable in one command* — which is the difference between an undergraduate project and a research deliverable.

#### Defendable claim

> *"Evaluation integrity enforced by `scripts/audit_eval_numbers.py` which verifies every number in `docs/evaluation/EVALUATION.md` against source data. Full evaluation reproducible via `make eval-reproduce`. All CVEs pre-registered in YAML before scanning to prevent post-hoc cherry-picking. Skipped CVEs logged with reasons in `docs/evaluation/INTEGRITY.md`."*

---

### TIER 1 — CVE Recall Test ⭐ (Highest Impact, 15h)

**The bulletproof move.** Use publicly-disclosed CVEs in major Python projects as ground truth. The CVE database is **external**, **published**, and **NIST-maintained** — you cannot be accused of biased labeling when MITRE did the labeling.

#### Methodology

1. Select **15–20 disclosed CVEs** across major Python projects (Django, Flask, Pillow, requests, PyYAML, urllib3, aiohttp, SQLAlchemy, Jinja2, Werkzeug)
2. For each CVE:
   - Find the commit SHA that introduced or contained the vulnerability (parent of the security patch)
   - Find the CVE entry's `affected_files` and `affected_lines` (often in the patch diff)
   - Clone the project at the **pre-fix commit**
   - Run ACR-QA: `python3 CORE/main.py --target-dir ./<project> --rich --no-ai`
   - **Score:** did ACR-QA flag a HIGH-severity finding on the vulnerable line(s)?
3. Report: **`X / N CVE recall on disclosed Python vulnerabilities`**

#### Why this is bulletproof

- Ground truth is **external** (NIST, MITRE, GitHub Security Advisories) — not authored by you
- Code is **real production** (Django + Flask + others are not toys)
- Result is **unambiguous** (caught the CVE line or didn't)
- Methodology mirrors **Snyk** and **Semgrep**'s own marketing materials
- Examiner cannot push back without arguing with the CVE database

#### CVE selection criteria

Pick CVEs that:
- ✅ Are in **active** Python projects (not abandoned packages)
- ✅ Have a clear `affected_lines` in the security patch diff
- ✅ Map to vuln categories ACR-QA targets (SQLi, command injection, path traversal, deserialization, XSS, hardcoded secrets, weak crypto, eval/exec)
- ❌ Skip CVEs that require runtime context (CSRF, IDOR, business logic) — out of scope for SAST

#### Candidate CVE categories (final list during execution)

| Category | Example projects to mine |
|---|---|
| SQL injection (CWE-89) | Django, SQLAlchemy, raw `cursor.execute` patches |
| Command injection (CWE-78) | `subprocess.run(shell=True)` fixes in CLI tools |
| Path traversal (CWE-22) | Pillow, Flask static-file handlers, archive extractors |
| Deserialization (CWE-502) | PyYAML, pickle-based caching libraries |
| Code injection / eval (CWE-94) | Template engines, config loaders |
| Hardcoded secrets (CWE-798) | Audited and removed in production patches |
| Weak crypto (CWE-327, CWE-328) | MD5/SHA1 → SHA256 migrations |

#### Deliverables

- `TESTS/evaluation/cve_recall/` directory with one YAML per CVE:
  ```yaml
  cve_id: CVE-2024-XXXXX
  project: Django
  vuln_commit_sha: <pre-fix commit>
  fix_commit_sha: <patch commit>
  affected_file: django/contrib/admin/views/main.py
  affected_lines: [142, 143]
  cwe: CWE-89
  acrqa_detected: true|false
  acrqa_finding_id: SECURITY-027
  notes: "Caught via Semgrep custom rule"
  ```
- `scripts/run_cve_recall.py` — automated harness
- `TESTS/evaluation/test_cve_recall.py` — pytest slow-marked
- `docs/evaluation/CVE_RECALL.md` — methodology + results table

#### Defendable claim

> *"ACR-QA detected the vulnerable code in X/N disclosed Python CVEs from major projects (Django, Flask, PyYAML, requests, Pillow). Ground truth pulled from MITRE/NIST. Methodology mirrors Snyk and Semgrep's published evaluations."*

This single sentence kills the "toy benchmarks" critique.

---

### TIER 2 — Peer Validation (3h, Inter-Rater Agreement)

Eliminates the "you graded your own homework" follow-up by having **independent reviewers** triage a sample of findings.

#### Methodology

1. Pick a 20-finding random sample from the Flask scan output (HIGH + MEDIUM)
2. Recruit **2 independent reviewers** — preferably:
   - Another CS student at KSIU
   - A peer from Dr. Samy's other supervisees
   - (Fallback: a developer friend with security background)
3. Provide each reviewer:
   - The 20 findings (rule_id, file, line, message, code snippet)
   - The rule definitions from `config/rules.yml`
   - Instructions: classify each as TP / FP / unsure
4. Compare reviewer labels against your labels
5. Compute **Cohen's kappa (κ)** for inter-rater agreement
6. Report: *"κ = 0.XX on 20-finding sample"*

#### Why this is research-grade

- κ > 0.80 = "almost perfect agreement" (Landis & Koch 1977)
- κ > 0.60 = "substantial agreement" — already publishable
- An examiner cannot say "you triaged your own tool" when 3 independent people agreed

#### Deliverables

- `docs/evaluation/PEER_VALIDATION.md`:
  - Reviewer 1, 2, 3 (anonymised) labels
  - Confusion table
  - κ calculation
  - Disagreement analysis (which findings split the reviewers, and why)

#### Defendable claim

> *"Inter-rater agreement between three independent reviewers on a 20-finding Flask sample: κ = 0.XX (substantial agreement, Landis & Koch). Disagreements documented and analysed."*

---

### TIER 3 — Real-World Corpus Expansion (8h, Coverage Gap Filler)

Adds 4 well-chosen real-world repos to plug specific gaps in language coverage. This is the original `EVAL_EXPANSION_PLAN.md` — kept because it's still useful, but **subordinate** to Tiers 1 and 2 in importance.

#### Identified gaps in current corpus

| Gap | Why It Matters |
|---|---|
| **No Go vulnerable target** | Ship Go adapter (gosec + staticcheck + Semgrep Go), evaluate only on gosec self-tests |
| **No pure TypeScript target** | JS adapter tested mostly on `.js` files |
| **No large real-world Python** | Flask is 68k★ but only ~10k LOC; need 50k+ LOC for scale claim |
| **Limited real-world Python** | Only Flask + httpx; FP rate validation needs more diversity |

#### The 4 repos

| Repo | Language | LOC | Fills gap |
|---|---|---:|---|
| **govwa** (Go Vulnerable Web App) | Go | ~3,000 | Go vulnerable target |
| **Django** (76k★) | Python | ~250,000 | Real-world Python diversity |
| **NodeGoat-TS variant** or hand-authored mini TS app | TypeScript | ~2,000 | Pure TS coverage |
| **FastAPI** (74k★) | Python | ~50,000 | Large-scale async Python |

#### Deliverables (per repo)

- `TESTS/evaluation/ground_truth/<repo>.yml`
- `TESTS/evaluation/test_recall.py` — one slow-marked test per repo
- Update to `docs/evaluation/EVALUATION.md` corpus tables

#### Defendable claim

> *"Evaluated across 16 repos spanning Python, JavaScript, TypeScript and Go — 10 ground-truth corpus + 6 real-world (Flask, httpx, Django, FastAPI, govwa, plus the new TS app)."*

---

## Effort Budget

| Tier | What | Hours | Defense impact |
|------|------|------:|:---:|
| 0 | Integrity infrastructure (audit script + reproduce target + charter) | **3** | 🔥🔥🔥🔥 |
| 1 | CVE Recall Test (15–20 CVEs) | **15** | 🔥🔥🔥🔥🔥 |
| 2 | Peer Validation (κ on 20-finding sample) | 3 | 🔥🔥🔥🔥 |
| 3 | Real-world corpus expansion (4 repos) | 8 | 🔥🔥 |
| **Total** | | **~29** | |

## Sequencing (Recommended)

**Critical path: Tier 0 first, always.** Without integrity infrastructure, the data from Tiers 1–3 is only as trustworthy as whoever typed it. Tier 0 enables every subsequent tier to be self-verifying.

1. **Tier 0 (Integrity, 3h)** — always do this first; cheapest insurance in the plan
2. **Tier 1 (CVE Recall, 15h)** — single biggest move; biggest defendable claim
3. **Tier 2 (Peer Validation, 3h)** — depends on reviewer availability; start recruitment early
4. **Tier 3 (Corpus expansion, 8h)** — useful but optional if defense is close

**Minimum viable rigor:** Tier 0 + Tier 1. Numbers are checkable AND backed by external ground truth.
**Recommended rigor:** Tier 0 + Tier 1 + Tier 2. Adds inter-rater κ for "graded your own homework" defense.
**Maximum rigor:** All four tiers. ~29h, but the eval section becomes unassailable.

## Decision Matrix Based on Defense Runway

| Time until defense | Recommendation |
|---|---|
| **> 4 weeks** | All four tiers — go bulletproof |
| **2–4 weeks** | Tiers 0 + 1 + 2 (skip corpus expansion) |
| **1–2 weeks** | Tiers 0 + 1 only (integrity + CVE recall) |
| **< 1 week** | At minimum Tier 0 (audit + reproduce script). Memorize the verbal pivot. |

**Note:** Tier 0 is **always recommended** regardless of runway. 3 hours of work makes every existing number self-verifying — that's value the supervisor sees instantly even if Tiers 1–3 are deferred.

## Success Criteria

- [x] **Tier 0:** `INTEGRITY.md` charter committed; `audit_eval_numbers.py` passing; `make eval-reproduce` works end-to-end ✅ 2026-05-17
- [x] **Tier 0:** Every number in `EVALUATION.md` auto-verified or documented exception in `INTEGRITY.md` ✅ 2026-05-17
- [x] **Tier 1:** 10 CVE recall tests pre-registered, automated; results in `docs/evaluation/CVE_RECALL.md` ✅ 2026-05-17 (2/10 = 20%, honest)
- [x] **Tier 1:** Defendable claim: "2/10 CVE recall on disclosed Python vulnerabilities from MITRE/NIST; each miss root-cause-analysed" ✅
- [x] **Tier 2:** Peer validation κ = 0.74 > 0.60, documented in `docs/evaluation/PEER_VALIDATION.md` ✅ 2026-05-17
- [x] **Tier 3:** 3 repos added (GoVWA, vulnerable-node, django.nV) — corpus now 13 repos, 4 languages ✅ 2026-05-17
- [x] **Overall:** `EVALUATION.md` §3b (CVE recall) + §3c (peer κ) + 13-repo corpus table ✅ 2026-05-17
- [x] **PRESENTATION_SCRIPT.md:** Q&A updated with κ=0.74, 2/10 CVE recall, 13 repos ✅ 2026-05-17

## Updated Numbers After Completion (All Tiers)

| Metric | Before | After |
|---|------:|------:|
| Total repos | 12 | 16 (+4 from Tier 3) |
| CVE recall tests | 0 | 15–20 (Tier 1) |
| Real-world repos with labels | 2 (FP-only) | 6 (full ground truth) |
| External ground truth sources | 0 | MITRE + NIST CVE database |
| Independent reviewers | 0 | 2 (Tier 2) |
| Auto-verified claims in EVALUATION.md | 0 | 100% (Tier 0) |
| One-command full eval reproducibility | ❌ no | ✅ `make eval-reproduce` (Tier 0) |
| Defendable corpus claim | "97.1% on 4 toy apps" | "X/N CVE recall + κ=0.XX peer validation + 16-repo 4-language corpus, all numbers auto-verified" |

---

## What's Explicitly NOT Added

- ❌ **Random GitHub vuln repos** — no signal without ground truth
- ❌ **OWASP Benchmark v1.2** — Java-only, Python ports unmaintained
- ❌ **Linux kernel** — overkill, 10h+ scan time, low signal
- ❌ **WebGoat / Mutillidae** — Java, out of scope
- ❌ **Closed-source enterprise samples** — can't ground-truth without internal docs
- ❌ **More toy benchmarks** — doesn't address the critique (this is THE critique!)

## Risks

| Risk | Mitigation |
|---|---|
| Can't find 15–20 clean CVEs with mappable lines | Plan for 10–12 minimum; report what we have honestly |
| Some CVEs not detectable by static analysis (runtime context) | Document `out_of_scope` reason per CVE; partial recall is still honest |
| Peer reviewers unavailable | Use 1 reviewer + author; still better than author-only; reduce to 10-finding sample if needed |
| Tier 1 surfaces real product bugs | This is a **win** — bugs found in eval are bugs fixed in product |
| Time pressure forces skipping Tier 1 | Use decision matrix above; brutal honesty about runway |
