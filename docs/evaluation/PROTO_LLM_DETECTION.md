# Prototype — LLM-Augmented Detection (Phase 0 result)

> **Generated:** 2026-06-03 · Phase 0 of `docs/GO_BIG_LLM_DETECTION_PLAN.md`
> **Model:** llama-3.3-70b-versatile (zero-shot, **single-file**, no cross-file context)
> **Corpus:** RealVuln repos (vampi, dsvpwa, flask-xss); scored vs ground truth (file+CWE+line±10)

## Result — three strictness levels (the diagnostic)

| Repo | strict (file+CWE+line) | file+line (ignore CWE) | file-only | false-alarm rate |
|---|:---:|:---:|:---:|:---:|
| vampi | 33% | 60% | 100% | ~80% |
| dsvpwa | 9% | 41% | 62% | ~83% |
| flask-xss | 20% | — | — | ~78% |
| **aggregate** | **~17%** | **~50%** | **~75%** | **~80%** |

Rule-based baseline for reference: **25.1% full / 37.8% detectable**.

## What this means (honest)

1. **The LLM is NOT detection-blind.** It localizes the vulnerable *file* 62–100% of the time. The low
   strict-recall is mostly **CWE mislabeling + line drift**, not failure to notice the bug.
2. **At file+line (~50%) it is competitive with / above the rule-based detectable subset (37.8%).** There
   is genuine recall potential here.
3. **But the false-alarm rate is ~80%** — the classic standalone-LLM precision collapse (cf. NDSS 2025,
   23–65% precision). Ungated, this is unusable.
4. **This is the hybrid thesis in miniature:** LLM supplies recall, *something* must supply precision.
   ACR-QA's exploit-verifier is that something — but only for the ~10 exploitable categories; secrets/
   crypto/config would need the LLM-jury (`second_opinion`) instead.

## Model sweep (live Groq, same 3 repos) — surprising + useful

| Model | LLM-alone recall | union lift | false-alarm rate | role |
|---|:---:|:---:|:---:|---|
| **llama-3.3-70b-versatile** | **22.1%** | **+13.0pp** | ~76% | aggressive **detector** (best recall) |
| meta-llama/llama-4-scout-17b | 15.6% | +9.1pp | ~73–96% | mid |
| openai/gpt-oss-120b | 10.4% | +6.5pp | **0–50%** | conservative **judge** (best precision) |
| qwen/qwen3-32b | 9.1% | +3.9pp | ~50–100% | conservative |

**Counter-intuitive finding:** newer/bigger reasoning models detect **fewer** vulns — they're tuned to be
cautious. The old `llama-3.3-70b` is the **best aggressive detector** on Groq. (Parsing note: gpt-oss/qwen
are reasoning models that emit answers in `.reasoning`, not `.content` — the harness now reads both.)

**The architecture this dictates:** models are a precision/recall **dial**. Use **llama-3.3-70b to DETECT**
(broad recall) → **gpt-oss-120b to GATE** (its low false-alarm rate = a strong judge). This is the
`second_opinion` design with empirically-chosen roles, and it **de-risks the gating step** the hybrid needs.

---

## UPDATE — the union test (the decisive product number)

LLM-*alone* is below rules. But the real question is **complementarity**: does the LLM catch what rules
miss? Measured rules-alone vs LLM-alone vs **union**, strict (file+CWE+line) matching:

| Sample | RULES | LLM-alone | UNION | **union lift** | LLM false-alarm |
|---|:---:|:---:|:---:|:---:|:---:|
| 3 repos | 15.6% | 22.1% | 28.6% | **+13.0pp** | ~76% |
| 6 repos | 18.5% | 17.0% | 27.4% | **+8.9pp** | ~80–90% |

**The lift is real and stable (~+9pp across 6 repos).** The LLM finds genuine vulns the rules miss — they
are complementary. Per-repo the lift ranges +0% to +10%.

## Verdict: GO on a SCOPED hybrid (not the SOTA rebuild) — achievable in days, data-backed

- **The recall win exists:** union +9pp means detectable recall could go ~37.8% → ~45%. Real, honest,
  defensible. **Not** "best of the bests" (that's the months-long agentic build) — but a genuine improvement.
- **The whole bet hinges on PRECISION:** the LLM half is 80–90% false alarms. The hybrid only works if
  gating (`second_opinion` two-LLM vote / `confirmed_tier` / exploit-verifier) keeps the +9pp recall while
  killing the FPs. **That is the next experiment, and the kill-switch.**
- **Scoped plan (days, mostly wiring existing engines):**
  1. ✅ DONE — union lift measured (+9pp, holds across 6 repos).
  2. Gate LLM candidates through `second_opinion`/`confirmed_tier`; measure precision retention.
  3. Held-out split on more repos — confirm the lift isn't sample noise.
  4. If gating holds precision → ship "LLM-augmented, gated detection" as a real result + novel hybrid.
  5. Re-benchmark + update docs/README/QA_PREP.
- **Kill-switch:** if step 2 shows gating can't keep precision (recall lift evaporates when FPs are cut),
  it reverts to Future Work and we defend on current numbers. **Decide on the gating data, not hope.**

## If pursued post-defense (the real "go big")

1. Cross-file/agentic context (not single-file zero-shot — the #1 handicap here).
2. CWE normalization: map LLM CWE output → RealVuln families (recovers the 17%→50% gap).
3. Exploit-gating for the 10 verifiable categories + calibrated LLM-jury for the rest.
4. Held-out split; report PR curve (LLM-augmented full output vs exploit-gated Confirmed Tier).

**Reproduce:** `python3 scripts/proto_llm_detection.py --repos realvuln-vampi realvuln-dsvpwa`
