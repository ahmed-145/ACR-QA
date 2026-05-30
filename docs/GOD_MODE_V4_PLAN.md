# ACR-QA God Mode Plan v4 — Precision Ceiling + Beyond-Defense Moves

**Created:** 2026-05-30 — after Track 4 fully complete (T4.1–T4.9 all done)
**Status:** ACTIVE — v3 is fully complete; this is the next horizon
**Owner:** Ahmed Mahmoud Abbas (KSIU, supervised by Dr. Samy AbdelNabi)
**Context:** Baseline is 24.7% conservative / 26.9% optimistic security-tier precision,
100% detectable CVE recall (11/11), Track 4 fully documented. Everything here
is additive — nothing regresses that.

---

## 0. What We're Going For

Two parallel tracks:

- **Track P (Precision):** Push security-tier conservative precision as high as
  defensible, in three escalating levers (data curation → corroboration tier →
  semantic gating). Realistic ceiling: **45–60% conservative** while keeping
  100% recall. This is the core thesis upgrade.

- **Track X (Expansion):** Novel evaluations and features that turn "we built a
  SAST tool" into "we ran a rigorous empirical study and proved the findings are
  real." Exploit verification, live-CVE generalization, AI-generated-code vuln study.

Execute **P first, in order P1 → P2 → P3**. Start **X1** in parallel once P1
is committed (it's read-only analysis, no regression risk).

---

## Track P — Precision Enhancement (do in order, gate on recall each time)

### P1 — Per-Rule Precision Floor (data-driven rule curation)
**Effort:** S (1 day) · **Recall risk:** LOW (verifiable) · **Expected gain:** +7–14pp conservative

**What:**
Compute standalone precision for every `(tool, canonical_rule_id)` pair on the
full 30-repo precision corpus. Quarantine (demote to MEDIUM or drop from
security-tier) any rule with <5% conservative precision **and** 0 AUTO_TP hits
across the corpus. Before dropping, verify on the recall corpus that no
detectable CVE relied on that rule.

**Why now:**
Cheapest lever left. Bandit `B5xx` rules (SECURITY-005, SECURITY-022 partial,
SECURITY-025, SECURITY-023) contribute large FP counts with near-zero TP. A
data-driven floor is defensible: "we kept every rule that catches real CVEs."

**Steps:**
1. Add `per_rule_precision()` function to `scripts/run_precision_benchmark.py`
   that groups triage results by `rule` and reports TP/FP/total/precision.
2. Print a sorted table: bottom-10 rules by precision.
3. For each rule with precision=0 and no recall-corpus hits: add to a new
   `QUARANTINE_RULES` set in the triage logic — treat as `AUTO_FP` at sec-tier.
4. Rerun benchmark + ablation + bootstrap. Report new numbers.
5. Run `pytest TESTS/test_eval_regression_guard.py` — confirm recall stays 100%.
6. Update EVALUATION_CHAPTER.md §5.4 with new Rung 3 row.

**Gate to P2:** Conservative precision ≥ 30% AND recall corpus still 11/11.

**Files touched:** `scripts/run_precision_benchmark.py`, `scripts/run_ablation_study.py`,
`TESTS/evaluation/results/`, `docs/EVALUATION_CHAPTER.md`, regression guard thresholds.

---

### P2 — High-Confidence Corroboration Sub-Tier
**Effort:** S–M (1–2 days) · **Recall risk:** ZERO (additive, not destructive) · **Expected precision:** 55–70%

**What:**
Do NOT remove the existing security-tier (Rung 3). ADD a "Rung 3.5 — High-Confidence"
tier: findings where ≥2 different tools flag the same `(repo, file, line ±3)`.
Report precision separately for this sub-tier. This is the two-tool agreement
signal we tried (and found 0 pairs) during T4 levers — but we apply it as a
*separate measurement*, not a filter.

**Why now:**
In practice, analysts in commercial SAST settings use corroboration as a
priority queue. Publishing this number gives the thesis a "high-confidence
analyst view" table row. Expected: smaller cohort, much higher precision.

**Steps:**
1. Add `corroboration_tier()` to `run_ablation_study.py`: for each finding in
   `security_tier_f`, check if another finding from a DIFFERENT tool is within
   3 lines in the same file. Call this the corroboration set.
2. Compute precision for the corroboration set separately.
3. Add a new row to the ablation table: "Rung 3.5 — Two-tool corroborated".
4. Add to `EVALUATION_CHAPTER.md` §5.4 with interpretation.
5. Add regression guard floor for corroboration-tier precision (≥ 50%).

**Gate to P3:** Corroboration tier has ≥ 5 findings AND precision ≥ 50%.
If fewer than 5 corroborated findings exist, skip P2 and note it honestly.

**Files touched:** `scripts/run_ablation_study.py`, `docs/EVALUATION_CHAPTER.md`,
`TESTS/test_eval_regression_guard.py`.

---

### P3 — Semantic Gating via Taint + Path Feasibility
**Effort:** L (3–5 days) · **Recall risk:** MEDIUM (gate carefully) · **Expected gain:** +15–25pp conservative

**What:**
Wire `taint_analyzer` and `path_feasibility` into the security-tier verdict.
For a finding to remain AUTO_TP at Rung 3, it must pass at least ONE semantic gate:

- A taint path exists from an entry point to the sink at this `(file, line)`, OR
- `path_feasibility` scores the call-chain as feasible (not dead-code-only), OR
- The finding is already in `HIGH_CONFIDENCE_RULES` and has corroboration (P2).

Findings that fail all gates get demoted to `NEEDS_REVIEW` (not AUTO_FP —
we don't want to hide real bugs, just flag ambiguity). The conservative
precision then rises because NR already counted as FP — but more importantly
this is the *principled* argument: "precision improved because we added
semantic evidence, not just curation."

**Why now:**
This is the thesis money shot. The committee question "why does precision
improve?" gets the answer "because we added inter-procedural taint evidence
and path feasibility scoring" — that's a paper-quality claim.

**Steps:**
1. Sketch the integration contract: what does `taint_analyzer.analyze(file, line)`
   return? What does `path_feasibility.is_feasible(file, line, rule)` return?
   Read both engines and write the interface in a design note first.
2. Add a `semantic_gate(finding) → bool` function in `run_precision_benchmark.py`
   that calls both engines on the cached precision corpus findings.
3. Rerun triage with semantic gate applied. Compute new precision.
4. Verify recall corpus: ALL detectable CVEs must still be detected.
5. If any CVE drops: add it to the `SEMANTIC_GATE_EXCEPTIONS` bypass list with
   an explicit reason (e.g., "taint path not traceable statically but vuln is
   confirmed by exploit verifier").
6. Update full eval suite: ablation, bootstrap CIs, EVALUATION_CHAPTER.md.

**Gate to Track X:** Conservative precision ≥ 40% AND recall still 11/11.

**Files touched:** `scripts/run_precision_benchmark.py`,
`CORE/engines/taint_analyzer.py` (read-only in eval context),
`CORE/engines/path_feasibility.py` (read-only in eval context),
all eval result JSONs, `docs/EVALUATION_CHAPTER.md`.

---

## Track X — Beyond-Defense Expansion (novel evaluations + features)

### X1 — Live-CVE Generalization Benchmark
**Effort:** M (2–3 days) · **Thesis value:** VERY HIGH · **Can run in parallel with P2/P3**

**What:**
Pick 15–20 real CVEs published in 2025–2026 that are NOT in our existing recall
corpus. Pin each to the pre-fix commit. Scan blind (without looking at the
advisory first). Report detection rate. This answers the committee's hardest
question: "did you overfit to your own eval set?"

**Why:**
Zero existing SAST papers have done this at this level of rigor (blind pre-fix
scan, with honest misses documented). It turns the recall section from
"8 pre-selected detectable CVEs" into "11 original + 10 blind holdout = 21/23
detectable CVEs on unseen data." Publishable as a standalone subsection.

**Steps:**
1. Pull CVEs from NVD with `cve_program/2025` or `2026` date range, filter for
   Python/JS packages. Target: injectable, deserialization, code execution.
2. For each: classify as statically-detectable vs. honest-miss (same taxonomy as Track 2).
3. Write ground-truth YAML files in `TESTS/evaluation/ground_truth/live_cve/`.
4. Run `scripts/run_cve_recall.py` (or extend it) against each pre-fix clone.
5. Report: N detected / M statically-detectable / K honest misses (documented).
6. Add §5.12 to `docs/EVALUATION_CHAPTER.md`: "Live-CVE Generalization — Blind Holdout".

**Files touched:** `TESTS/evaluation/ground_truth/live_cve/` (NEW),
`scripts/run_cve_recall.py`, `docs/EVALUATION_CHAPTER.md`.

---

### X2 — Exploit Verification Eval (PoC demo on recall corpus)
**Effort:** M–L (3–5 days) · **Thesis value:** EXTREMELY HIGH · **Requires Docker**

**What:**
`CORE/engines/exploit_verifier.py` exists but is not evaluated. For each of the
11 confirmed-TP CVEs in the recall corpus:
1. ACR-QA detects the finding.
2. `exploit_verifier` generates or loads a PoC for that CVE.
3. PoC is run inside a Docker sandbox against the pinned-commit code.
4. Exploit succeeds → finding is confirmed exploitable (not just detectable).
5. Patch is applied (or the fix commit is checked out).
6. PoC is run again → exploit fails → finding is confirmed fixed.

This is the "detect → prove → fix cycle" demo. Almost no academic SAST thesis
goes this far.

**Steps:**
1. Read `exploit_verifier.py` end-to-end. Document what it actually does vs.
   what it claims. Fix any gaps.
2. Write `scripts/run_exploit_verification.py`:
   - Load recall corpus CVE ground truths
   - For each CVE: trigger scan → capture finding → call exploit_verifier
   - Run PoC in Docker (`TESTS/samples/Dockerfile` already exists)
   - Report: exploit_confirmed / exploit_failed / sandbox_error
3. Target: ≥ 3 confirmed exploitable CVEs end-to-end.
4. Write `docs/evaluation/EXPLOIT_VERIFICATION.md`.
5. Add §5.13 to `EVALUATION_CHAPTER.md`.

**Prerequisite:** Docker daemon running. `TESTS/samples/Dockerfile` usable.

**Files touched:** `scripts/run_exploit_verification.py` (NEW),
`CORE/engines/exploit_verifier.py` (possible fixes), `docs/evaluation/EXPLOIT_VERIFICATION.md`,
`docs/EVALUATION_CHAPTER.md`.

---

### X3 — AI-Generated Code Vulnerability Study
**Effort:** M–L (3–5 days) · **Thesis value:** VERY HIGH · **Novel + publishable**

**What:**
Collect 100 Python/JS code samples generated by LLMs (Claude, GPT-4, Gemini,
CodeLlama) for 20 common programming tasks (file I/O, DB query, HTTP request,
auth, crypto, subprocess, YAML parsing, etc.). Run ACR-QA on every sample.
Report:
- Vulnerability density (findings/KLOC) by model
- Which models produce which vulnerability classes most often
- Comparison with human-written equivalents from the precision corpus

**Why:**
Nobody has published this at scale yet. The paper angle is:
"AI coding assistants introduce security vulnerabilities at a measurable rate;
here is the first empirical benchmark." ACR-QA is the instrument, not the subject —
but it's still *your* paper.

**Steps:**
1. Define 20 programming tasks with standardized prompts.
2. Generate 5 samples per task per model = 100 samples per model × 4 models = 400 samples.
3. Save samples to `TESTS/evaluation/ai_code_samples/<model>/<task_N>.py`.
4. Run ACR-QA on each directory. Export findings to JSON.
5. Compute: findings/KLOC, HIGH findings/KLOC, security-tier precision by model.
6. Write `scripts/run_ai_code_study.py` and `docs/evaluation/AI_CODE_STUDY.md`.
7. Add §5.14 to EVALUATION_CHAPTER.md.

**Note:** LLM generation can be scripted via the Groq API (free, fast).

**Files touched:** `TESTS/evaluation/ai_code_samples/` (NEW, gitignored if large),
`scripts/run_ai_code_study.py` (NEW), `docs/evaluation/AI_CODE_STUDY.md`,
`docs/EVALUATION_CHAPTER.md`.

---

### X4 — Time-Travel Predictive Risk Backtest
**Effort:** L (5–7 days) · **Thesis value:** HIGH · **Genuinely novel**

**What:**
`CORE/engines/time_travel.py` and `risk_predictor.py` exist but are unevaluated.
The claim: ACR-QA can *predict* which files are likely to develop CVEs in the
future based on current code patterns. Backtest this on a real project:

1. Pick Django (well-documented CVE history, available via git).
2. For each of 20 release commits from 2018–2022, run `risk_predictor` and
   record the top-10 highest-risk files.
3. For each commit, look at which files *actually* got CVEs in the next 12 months.
4. Compute: were the predicted high-risk files significantly more likely to get
   CVEs than random files? (Chi-squared or Fisher's exact test.)

**Steps:**
1. Read `time_travel.py` and `risk_predictor.py`. Document what they compute.
2. Write `scripts/run_time_travel_backtest.py`.
3. Clone Django. For each of 20 historical commits: run scan → extract risk scores
   → record top-N files → compare to Django CVE file list from NVD.
4. Statistical test: precision/recall of the risk predictor.
5. Write `docs/evaluation/TIME_TRAVEL_BACKTEST.md`.

**Files touched:** `scripts/run_time_travel_backtest.py` (NEW),
`docs/evaluation/TIME_TRAVEL_BACKTEST.md`, `docs/EVALUATION_CHAPTER.md`.

---

### X5 — Head-to-Head Published Benchmark
**Effort:** M (2–3 days) · **Thesis value:** HIGH · **Committee-facing**

**What:**
Run ACR-QA, Semgrep CE, Bandit standalone, and Snyk free tier against the
same 30-repo precision corpus AND the recall corpus. Publish a single table
with precision, recall, analyst-hours, CVE detection rate, and unique
capabilities (ECDSA provenance, multi-tool dedup, AI explanation, etc.).

This is the "comparison with baselines" section every thesis committee expects,
but done with full corpus transparency and reproducibility scripts rather than
selective benchmarking.

**Steps:**
1. Script Semgrep CE, Bandit, and Snyk runs against all 30 precision repos.
   (Snyk free: `snyk test` via CLI, or skip if auth is painful.)
2. Collect findings. Apply same triage heuristics for FP estimation.
3. Run all three on recall corpus — measure CVE detection rate.
4. Write `scripts/run_head_to_head.py` and `docs/evaluation/HEAD_TO_HEAD.md`.
5. Update `EVALUATION_CHAPTER.md` §5.10 comparison table with real measured numbers
   (replace estimates).

**Files touched:** `scripts/run_head_to_head.py` (NEW), `docs/evaluation/HEAD_TO_HEAD.md`,
`docs/EVALUATION_CHAPTER.md` §5.10.

---

## Execution Order — Merged (optimal parallelism)

```
Step 1 ── P1 alone (1 day)
           Per-rule precision floor. Must come first — sets the baseline
           everything else builds on. Gate: conservative ≥ 30%, recall 11/11.

Step 2 ── P2 ∥ X1 (1–3 days, run simultaneously)
           P2: corroboration sub-tier (additive, no regression risk)
           X1: live-CVE blind holdout (pure recall analysis, zero pipeline touch)
           Gate for P2: ≥5 corroborated findings at ≥50% precision.
           X1 finishes independently — no gate needed.

Step 3 ── P3 ∥ X3 (3–5 days, run simultaneously)
           P3: semantic taint+path gating (the money shot)
           X3: AI-generated code vuln study (only needs Groq API, fully independent)
           Gate for P3: conservative ≥ 40%, recall 11/11.
           X3 finishes independently.

Step 4 ── X2 alone (3–5 days)
           Exploit verification eval. Needs P3 stable (final findings pipeline)
           and Docker. Most intensive — deserves its own focused slot.

Step 5 ── X4 alone (5–7 days)
           Time-travel predictive backtest. Longest, most novel. Runs after
           exploit work — shares the "prove findings are real" narrative arc.

Step 6 ── X5 alone (2–3 days)
           Head-to-head benchmark. Must come last — needs P3 final numbers
           to make the comparison table honest and publishable.
```

**Calendar sketch (assuming sequential days, no parallel execution):**
```
Day  1      → P1
Day  2–3    → P2 + X1 (parallel)
Day  4–8    → P3 + X3 (parallel)
Day  9–13   → X2
Day 14–20   → X4
Day 21–23   → X5
────────────────
~23 days total (down from ~28 if run strictly sequentially)
```

---

## Expected Final Numbers (after all of Track P)

| Metric | Now | After P1 | After P2 | After P3 |
|--------|:---:|:--------:|:--------:|:--------:|
| Sec-tier conservative | 24.7% | ~32–38% | N/A (new tier) | ~45–60% |
| Sec-tier optimistic | 26.9% | ~35–42% | N/A | ~48–63% |
| High-confidence tier | — | — | ~55–70% | ~65–80% |
| NR remaining | 5 | ~3 | ~1 | ~0–1 |
| CVE recall | 100% | 100% (gated) | 100% | 100% (gated) |

These are estimates. After each gate, recompute from data.

---

## What Each Move Tells the Committee

| Move | Defends against |
|------|----------------|
| P1 — rule curation | "Why do you keep rules with 0% precision?" |
| P2 — corroboration tier | "How would an analyst actually use this?" |
| P3 — semantic gating | "Why does your precision improve — just luck or real signal?" |
| X1 — live-CVE holdout | "Did you overfit your recall corpus?" |
| X2 — exploit verification | "Are your findings actually exploitable?" |
| X3 — AI-code study | "What's the real-world impact of this research?" |
| X4 — time-travel backtest | "Can your tool predict future vulnerabilities?" |
| X5 — head-to-head | "How does this compare to existing tools?" |

---

## Invocation

Run in merged step order:

- `go god mode P1`      → Step 1: per-rule precision floor (START HERE)
- `go god mode P2 X1`   → Step 2: corroboration sub-tier + live-CVE holdout (parallel)
- `go god mode P3 X3`   → Step 3: semantic gating + AI-code study (parallel)
- `go god mode X2`      → Step 4: exploit verification eval
- `go god mode X4`      → Step 5: time-travel backtest
- `go god mode X5`      → Step 6: head-to-head benchmark (last — needs final P3 numbers)

---

*Plan v4 supersedes nothing in v3 — v3 is fully complete. All v4 items are additive.*
*Start date: 2026-05-30. Update status markers (⏳/✅) here as each task lands.*
