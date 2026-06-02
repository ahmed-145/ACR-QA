# ACR-QA God Mode Plan v7 — Compete to Win

> **Created:** 2026-06-02
> **Author:** Ahmed Mahmoud Abbas
> **Trigger:** The P-1 SecurityEval benchmark (64.3% file-level precision, n=14, CI overlapping
> Semgrep) was a wake-up call. The bare precision claim is contestable. This plan is the response:
> stop leaning on one fragile number, build the things competitors *structurally cannot copy*, and
> measure ourselves on the *standardized* corpora the field actually respects.
>
> **Companion docs:** `GOD_MODE_V6_BUSINESS_PLAN.md` (positioning + business), `ACTIVE_ROADMAP.md`
> (the free execution list). v7 is the *competitive* layer — how ACR-QA becomes genuinely
> best-in-class, not just well-positioned.
>
> **Mantra:** *Don't win the precision argument. Make the precision argument irrelevant by proving
> exploitability and signing the proof — then publish the benchmark everyone else has to cite.*

---

## 0. The Reckoning — honest competitive standing (2026-06-02)

| Dimension | Honest status | Evidence |
|-----------|---------------|----------|
| Precision (bare number) | **Contestable** | P-1: 64.3% file-level [38.8%, 83.7%], n=14. Semgrep 71.2%. CIs overlap → no winner proven. |
| Recall | **Behind** | Confirmed Tier 3.6% on SecurityEval (by design — 22 rules vs ~75 CWEs). Bandit 39%, Semgrep 16.7%. |
| Exploit verification | **Uncontested lead** | No competitor runs real payloads in a sandbox. This is the moat the benchmark can't touch. |
| Attestation / provenance | **Uncontested lead** | ECDSA + Rekor + SLSA L3. Nobody signs findings. |
| CVE recall | **Strong** | 8/8 detectable CVEs (100%) on the pre-registered battery. |
| Benchmark rigor | **Weak today** | File-level matching, tiny n, self-chosen corpora. Fixable — and the field has standards (OWASP Benchmark, SastBench/MCC). |
| Auto-remediation | **Behind the frontier** | Snyk Agent Fix: 80% accuracy + retest. Apiiro: reachability-validated fixes. We have autofix but no verified-fix loop. |

**The brutal one-liner:** ACR-QA's *headline stat* is weaker than advertised, but its *architecture* (verify + attest) is ahead of everyone. v7 rebalances the story onto the architecture and makes the stats unimpeachable.

### ✅ V7-0 DONE (2026-06-02) — credibility fixed, and the recall story is now a *win*

The P-1 benchmark was found to be methodologically broken (it scored against Copilot's *secure*
completions and penalized correct silence). The rigorous **P-2 benchmark** (`scripts/run_benchmark_p2.py`)
fixes it — genuinely-vulnerable corpus, full detection, bootstrap CIs:

| Tool | Recall (detectable CWEs, n=89) | 95% CI |
|------|:------------------------------:|--------|
| **ACR-QA (full output)** | **58.4%** | [47.2%, 67.4%] |
| Bandit | 50.6% | [39.3%, 60.7%] |
| Semgrep CE | 23.6% | [14.6%, 32.6%] |

**ACR-QA detects more real vulnerabilities than either competitor** — near-perfect on high-severity
classes (cmd-injection 2/2, SQLi 2/2, deserialization 4/4, XXE 6/6, SSRF 2/2). Full honest write-up +
P-1 retraction: `docs/evaluation/RECONCILIATION.md`. This converts §0's "weak headline stat" into a
defensible best-in-class recall result. Remaining rigor items (OWASP Benchmark, MCC reporting) still
open under Track A.

---

## 1. North Star — what "best" means

> **ACR-QA is the only code-review tool that proves a vulnerability is real (by exploiting it),
> proves the fix closed it (by re-exploiting and failing), and signs both as tamper-evident
> evidence — measured on the field's own standardized benchmarks.**

Three pillars, each a thing competitors *structurally* lack:
1. **Verified Detection** — exploit it in a sandbox, or don't claim it's confirmed.
2. **Verified Remediation** — re-exploit the patched code; only call it fixed if the exploit now fails.
3. **Verified Provenance** — sign detection + fix as a cryptographic chain auditors can replay.

Everything else (precision %, recall %, rule count) is table stakes we keep competitive but stop
*leading* with.

---

## 2. Competitive Map (2026 research-grounded)

| Competitor | 2026 capability | Where they beat us today | Where we beat them — permanently |
|---|---|---|---|
| **Snyk Code + Agent Fix** | 80% autofix accuracy, 84% MTTR cut, retests fixes with *static* engine | Brand, autofix maturity, recall | They retest statically; we retest by *re-exploiting*. We attest. |
| **Semgrep** | Deterministic engine, custom rules, dev love | Recall, rule ecosystem, precision-at-n on SecurityEval | No exploit proof, no attestation. We sit on top of Semgrep. |
| **Apiiro AI-SAST** | Call+data flow + reachability + AI validation, fixes | Reachability maturity, runtime context | No DAST exploit proof, no public attestation standard. |
| **Checkmarx Assist** | Agentic fixes for logic flaws | Enterprise depth, logic-flaw reach | Closed, no signed provenance, no open benchmark. |
| **CodeRabbit** | $40M ARR, AI PR review UX | Distribution, momentum, UX | Different job — they review broadly; we *prove security* findings. |
| **GitHub Advanced Security / CodeQL** | Native, deep dataflow | Distribution, dataflow engine | We feed GHAS via SARIF + add attestation it lacks. |
| **Claude Code Security** | Frontier model, logic-bug depth | Model quality, distribution | No exploit-sandbox proof, no signing. We can verify *its* output. |

**Pattern:** the entire field has converged on *detect → validate → fix*. The validation everyone
does is **static reachability + AI reasoning**. The fix-retest everyone does is **static re-scan**.
**Nobody runs the actual exploit, and nobody re-runs it after the fix.** That gap is ACR-QA's
permanent territory. v7 plants the flag there and fortifies it.

---

## 3. Track A — Benchmark Credibility & Scientific Rigor

*Goal: make the numbers unimpeachable. Replace self-chosen corpora + crude matching with the field's
own standards. This directly answers the "64 vs 96" problem.*

- **A1 — Run on OWASP Benchmark for Python (v0.1→v1.0).** The standardized corpus: each test case has
  a *single intentional CWE*, labeled True/False in `expectedresults-1.2.csv`. CWE-level matching, not
  file-level. This is the benchmark examiners and buyers recognize. **Exit: published OWASP Benchmark
  score with the official scorecard tooling.**
- **A2 — Adopt SastBench + MCC metric.** SastBench (arxiv 2601.02941) evaluates agentic SAST triage
  with Matthews Correlation Coefficient (robust to class imbalance) + precision/recall/F1/F2. Report
  MCC everywhere — it's the rigorous metric for imbalanced detection. **Exit: MCC reported alongside
  precision/recall in every benchmark.**
- **A3 — CWE-level matching in P-1.** Upgrade `run_benchmark_p1.py`: a finding is TP only if its
  canonical rule's CWE matches the file's labeled CWE. Removes the file-level noise that produced the
  misleading 64.3%. **Exit: P-1 re-run with CWE matching + bootstrap CIs.**
- **A4 — Manual triage of every Confirmed finding.** For each Confirmed Tier finding on any benchmark,
  hand-verify: real vuln? exploitable? This is the integrity move — if 12/14 are genuinely real, true
  precision ≈ 90% and the file-level 64% is shown to *understate*. Document the triage. **Exit: a
  triaged ground-truth table, examiner-defensible.**
- **A5 — Power the sample.** n=14 is too small; CI [38.8%, 83.7%] is useless. Combine OWASP Benchmark
  (~2,700 cases, Python port) + full SecurityEval (Copilot + InCoder + Insecure) + the CVE battery →
  n>200 → tight CIs. **Exit: every headline stat has a CI narrower than ±10pp.**
- **A6 — Pre-register everything, publish the unflattering.** Every benchmark methodology committed to
  git *before* running. Report results even when we lose. **This is what earns examiner and reviewer
  trust** — and it's the opposite of being "cooked." **Exit: a `docs/evaluation/RECONCILIATION.md` that
  honestly explains why internal-triage (96.4%) and file-level (64.3%) differ, and gives the
  CWE-level number as the reconciled truth.**

---

## 4. Track B — The Uncontestable Moat: Verified Detection

*Goal: widen the exploit-verification lead so far that "did you actually exploit it?" becomes the
question every buyer asks every competitor.*

- **B1 — Expand exploit categories.** Today: SQLi, command injection, SSTI, path traversal. Add: SSRF,
  XXE, insecure deserialization (pickle/yaml RCE), open redirect, auth-token leakage. Each with a safe
  PoC payload + sandbox harness. **Exit: ≥10 exploit categories, each with a passing demo.**
- **B2 — Multi-language exploit verification.** Extend the Docker-sandbox verifier to JS/Express and
  Go/net-http targets, not just Python/Flask. **Exit: one JS + one Go exploit verified end-to-end.**
- **B3 — Reachability score (beat Apiiro/Endor at their own game).** Fuse taint + call-graph +
  dependency reachability into a single 0–100 `reachability_score`. Gate Confirmed Tier on it. This is
  the feature Endor/Apiiro lead on — match and exceed by combining it with *actual* exploitation.
  **Exit: reachability_score on every finding; Confirmed Tier requires score ≥ threshold OR
  exploit-verified.**
- **B4 — LLM-as-judge for non-exploitable-class findings.** Web vulns get DAST proof; logic/crypto/
  config findings can't be Docker-exploited. For those, a structured multi-model jury (Groq + Gemini)
  estimates exploitability with a *calibrated* confidence and a cited rationale. Extends "verification"
  to 100% of findings, not just the web-injectable subset. **Exit: every finding has either a DAST
  verdict or a calibrated jury verdict.**
- **B5 — Calibrated confidence as a first-class output.** Stop shipping a bare "tier." Ship a
  probability with a reliability diagram + Expected Calibration Error (ECE). "When we say 90%, it's
  right 90% of the time" — provable, scientific, and a genuine research contribution. **Exit: ECE < 0.1
  reported on the held-out corpus.**

---

## 5. Track C — Verified Remediation (the frontier move)

*Goal: leapfrog the entire agentic-fix race. Everyone generates fixes and retests statically. We
generate a fix, re-run the actual exploit, and only call it fixed if the exploit now fails — then sign
the before/after.*

- **C1 — Verified-fix loop.** Pipeline: detect → exploit-verify (exploit fires) → autofix generates
  patch → apply patch in sandbox → **re-run the exact same exploit** → confirm it now fails → mark
  `fix_verified=true`. Snyk retests with a static engine (80% accuracy); we retest with the live
  exploit (ground truth). **Exit: ≥3 vuln classes where a generated fix is proven to close the exploit
  in-sandbox.**
- **C2 — Attested remediation chain.** Sign the tuple `(vuln_proof, fix_diff, fix_proof)` as one
  ECDSA-attested, Rekor-logged record. An auditor can replay: "here's the exploit working, here's the
  patch, here's the exploit failing — cryptographically chained." **Nobody else signs the fix.**
  **Exit: a signed remediation bundle in the Verified Finding v2 schema.**
- **C3 — Fix-quality gate.** Reject any fix that (a) doesn't close the exploit, (b) breaks tests, or
  (c) introduces a new finding. Multi-criteria, like Snyk's pre-screening but exploit-grounded.
  **Exit: 0 regressions in the verified-fix corpus.**
- **C4 — MTTR metric.** Track mean-time-to-remediation like the incumbents (Snyk claims 84% cut). Ours
  is *verified* MTTR — time to a fix proven to close the exploit. **Exit: published verified-MTTR.**

---

## 6. Track D — AI-Native Differentiation (ride the +107% wave)

*Goal: be THE tool for reviewing AI-generated code, the fastest-growing and most-vulnerable code
category (1.88× more flaws, +107% vulns/codebase YoY).*

- **D1 — AI-code diff mode → production-grade.** The `ai_code_diff.py` heuristics (git + headers) get a
  third signal: per-hunk style/entropy analysis to flag "pasted from assistant" code with no author
  history. **Exit: precision/recall of AI-authorship detection measured on a labeled set.**
- **D2 — AI-assistant-specific rule pack.** AI code has characteristic failure modes (hardcoded
  example secrets, missing input validation on scaffolded endpoints, copy-pasted insecure snippets).
  A dedicated rule pack tuned to these. **Exit: a measurable lift in detection on the AI-generated
  subset vs human-written.**
- **D3 — IDE / agent-loop integration.** Hook into the Copilot/Cursor/Claude Code loop: as the AI
  writes, ACR-QA verifies in the background and blocks insecure suggestions before commit. The
  incumbents (Endor AURI, Checkmarx) are moving here — match them but with exploit proof. **Exit: a
  VS Code extension path that surfaces Confirmed findings inline.**
- **D4 — The verification data flywheel → public asset.** Every exploit verdict is labeled ground
  truth (the `verification_log` table). At scale this becomes a *published dataset* — "the largest
  corpus of (finding → did-it-exploit) labels." Owning a dataset others cite = owning the category.
  **Exit: a versioned, anonymized export of the verification corpus.**

---

## 7. Track E — Own the Benchmark (category leadership)

*Goal: don't just score well on benchmarks — publish the benchmark everyone else has to run. The way
tools cite OWASP Benchmark and SARIF, make them cite ACR-QA's.*

- **E1 — The Verified Finding open standard (v2).** Extend `schemas/verified_finding_v1.schema.json`
  with the remediation chain (C2). Push for adoption: if any other tool emits Verified Findings, we're
  the standard. Moats made of standards are the strongest a small team can build (cf. SARIF, SLSA).
  **Exit: spec published + ≥1 external citation or adopter.**
- **E2 — Public live leaderboard (P-2 → real).** `cloudflare-pages/benchmark.html` re-runs weekly in
  CI on OWASP Benchmark + SecurityEval, signs the result JSON, publishes to Rekor. "Continuously
  falsifiable" is itself the marketing. Include competitors honestly. **Exit: CI job live, results
  signed.**
- **E3 — The Exploitability Benchmark.** Create a NEW benchmark the field lacks: not "did you detect
  it?" but "did you *prove* it exploitable?" Most tools score 0 because they can't. We define the
  category and the metric. **Exit: `docs/evaluation/EXPLOITABILITY_BENCHMARK.md` + a runnable harness.**
- **E4 — Publish the paper.** "Verified Findings: DAST-augmented SAST with attested remediation and
  calibrated confidence." The honest 64-vs-96 reconciliation becomes a *methodology contribution*
  (how crude matching misleads SAST benchmarks). Target a security venue or arXiv. **Exit: arXiv
  preprint.**

---

## 8. Track F — Product, Platform & Performance

*Goal: the experience and scale of a real product, not a thesis demo.*

- **F1 — Sub-second incremental PR feedback.** Differential scanning (only-new-findings) + caching so a
  PR check returns in seconds, not minutes. Performance is a feature buyers feel daily. **Exit: p95 PR
  scan < 10s on a 5k-LOC diff.**
- **F2 — The "one number" PR check.** A single required GitHub status: *N findings you can trust*.
  Click → exploit replay + "verify attestation" button. Already scaffolded; make it the default UX.
- **F3 — Scale hardening.** The verification_log + findings tables under load; connection pooling;
  rate limits; graceful degradation when Docker/LLM absent (already partial). **Exit: load test at
  100 RPS, p95 < 300ms on read paths.**
- **F4 — Multi-tenant org model + RBAC.** For the Team/Enterprise tiers — orgs, per-org triage memory,
  SSO. **Exit: org isolation + per-org confirmed-fix-rate KPI.**

---

## 9. Track G — Go-To-Market & Distribution

*(Cross-references GOD_MODE_V6_BUSINESS_PLAN.md §9 — summarized here for completeness.)*

- **G1 — 5 design partners** generating real verification data + case studies (P-3).
- **G2 — Research content engine.** Publish the AI-code vuln study, the exploitability benchmark, the
  64-vs-96 reconciliation as *industry research*. This is the content the market is searching for.
- **G3 — Land in security, expand to every PR.** Wedge: AppSec lead buys for verified-block +
  compliance; once it's a required check, every dev touches it.
- **G4 — File a real CVE (P-4).** From a real scan. Biggest single credibility unlock.

---

## 10. Track H — Academic & Defense Excellence

*Goal: the thesis defense is a showcase, and the work is genuinely publishable.*

- **H1 — The honest-science narrative.** Lead the defense with the reconciliation: "We pre-registered,
  we ran the independent benchmark, the file-level number was lower, here's why, here's the rigorous
  CWE-level number." Examiners reward intellectual honesty over inflated stats.
- **H2 — Three defensible novel contributions:** (1) DAST-augmented SAST with exploit verification,
  (2) attested verified remediation (re-exploit-after-fix), (3) calibrated confidence with ECE. Each is
  paper-worthy and none exists in competitors.
- **H3 — Reproducibility package.** Everything runnable in 2 commands, datasets pinned, results signed.
  **Exit: a Zenodo DOI for the replication package.**

---

## 11. The Killer New Ideas (the "think big" list)

These are the moves that make ACR-QA *category-defining*, not just competitive:

1. **Verified Remediation** (Track C) — re-exploit after fix. The whole industry retests statically;
   we retest by exploitation. This single feature obsoletes "80% autofix accuracy" claims with "100%
   of our verified fixes are proven to close the exploit."
2. **The Exploitability Benchmark** (E3) — invent the benchmark where every competitor scores ~0
   because they can't exploit. Define the category; own the metric.
3. **Calibrated confidence + ECE** (B5) — turn "trust" from a marketing word into a measured,
   provable probability. No SAST tool reports calibration error.
4. **Public verification corpus** (D4) — the data flywheel becomes a cited dataset. Own the ground
   truth others train on.
5. **Attested remediation chain** (C2) — sign vuln-proof + fix + fix-proof as one replayable record.
   Compliance gold; nobody signs the fix.
6. **The honest reconciliation as a research contribution** (A6/E4) — "how crude matching misleads
   SAST benchmarks" is a real paper. Turn the weakness into a publication.

---

## 12. Phased Execution

| Phase | Weeks | Focus | Exit metric |
|-------|-------|-------|-------------|
| **V7-0 Credibility** ✅ | 0–3 | ~~A3 CWE-matching, A4 reconciliation doc~~ DONE — P-2 benchmark + RECONCILIATION.md; ACR-QA 58.4% recall beats Bandit 50.6% / Semgrep 23.6% | ✅ Reconciled recall published with bootstrap CI |
| **V7-1 Standard corpora** | 3–6 | A1 OWASP Benchmark Python, A2 MCC, A5 power the sample | Official OWASP Benchmark scorecard + MCC, n>200 |
| **V7-2 Widen the moat** | 6–10 | B1 exploit categories, B3 reachability score, B5 calibration | ≥10 exploit classes, ECE<0.1 |
| **V7-3 Verified Remediation** | 10–16 | C1 fix loop, C2 attested chain, C3 quality gate | ≥3 classes with proven-closed fixes, signed |
| **V7-4 Own the benchmark** | 16–24 | E1 spec v2, E2 live leaderboard, E3 exploitability benchmark | External adopter/citation + live signed leaderboard |
| **V7-5 Publish** | 24–32 | E4 paper, H3 Zenodo, D4 public corpus | arXiv preprint + DOI |

Sequence rationale: **fix the credibility first** (cheap, high-integrity, defense-critical), then make
numbers unimpeachable on standard corpora, then widen the structural moat, then ship the frontier
feature (verified remediation), then convert it all into category ownership and publication.

---

## 13. Scorecard — "best-in-class" definition

| Dimension | Today | Best-in-class (10/10) | Track |
|---|:--:|---|:--:|
| Benchmark rigor | 3 | OWASP Benchmark + MCC + tight CIs + pre-registered + reconciled | A |
| Exploit verification | 8 | ≥10 classes, multi-language, the field's reference | B |
| Verified remediation | 1 | Re-exploit-after-fix, attested chain — unique in market | C |
| Calibrated trust | 2 | ECE<0.1, reliability diagrams, probability not tier | B5 |
| AI-code coverage | 5 | Best detector for AI-generated code, measured | D |
| Category ownership | 2 | Verified Finding standard cited; exploitability benchmark adopted | E |
| Product/scale | 5 | sub-10s PR, multi-tenant, 100 RPS | F |
| Academic | 6 | Published paper + DOI + 3 novel contributions | H |

**The single highest-leverage move right now:** Track V7-0 (credibility) — it's cheap, it's the
defense-critical fix, and it converts the benchmark "scare" into a strength. Do it first, this week.

---

## 14. Kill Criteria (intellectual honesty)

- If, on **OWASP Benchmark Python** (the standard corpus, CWE-matched), ACR-QA's full output can't
  match Semgrep's recall at comparable precision → the detection engine isn't differentiated; pivot
  the *entire* story to Verified Remediation + attestation (Tracks C+E) and stop competing on detection.
- If **Verified Remediation** can't close exploits reliably (>20% of generated fixes fail to close the
  exploit and can't be auto-repaired) → demote it to "assisted fix" and lead with verified *detection*.
- If **calibration** can't get ECE under ~0.15 → drop the calibrated-probability claim; keep the tier.

**Being "cooked" is not having a low number. Being cooked is hiding it.** v7's entire spine is: run the
hard benchmarks, report honestly, and win on the things — exploit proof, verified fixes, signed
provenance — that no competitor can contest regardless of what the precision number says.

---

## Sources (2026-06-02 research)

- [OWASP Benchmark Project](https://owasp.org/www-project-benchmark/) — standardized SAST corpus, Python v0.1→v1.0
- [OWASP Benchmark Framework overview](https://www.emergentmind.com/topics/owasp-benchmark)
- [SastBench: Agentic SAST Triage Benchmark (arXiv 2601.02941)](https://arxiv.org/html/2601.02941v1) — MCC metric
- [ZeroFalse: Improving Precision in Static Analysis with LLMs (arXiv 2510.02534)](https://arxiv.org/pdf/2510.02534)
- [Snyk Agent Fix field test 2026](https://safeguard.sh/resources/blog/snyk-agent-fix-autofix-field-test-2026) — 80% autofix, retest loop
- [Apiiro AI-SAST — detect, validate, fix with reachability](https://www.globenewswire.com/news-release/2025/12/18/3207774/0/en/Apiiro-Launches-AI-SAST-That-Detects-Validates-and-Fixes-Code-Vulnerabilities-with-Software-Architectural-Context-from-Code-to-Runtime.html)
- [Agentic Remediation: control layer for AI-generated code](https://softwareanalyst.substack.com/p/agentic-remediation-the-new-control)
- [Best SAST Tools 2026 — Corgea](https://corgea.com/learn/best-sast-tools)
