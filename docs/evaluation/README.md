# Evaluation Docs — Index

Provenance for every headline number in the thesis (Chapter 5). The thesis reproduces the
figures directly; these files are the underlying derivation, methodology, and raw evidence.
**Nothing here is deleted** — dated raw-run snapshots live in [`snapshots/`](snapshots/).

> Headline results: **P4 Confirmed Tier 96.4% cons / 100% opt precision** (95% CI [90.9%, 100%]),
> **100% CVE recall** (8/8 detectable), **RealVuln 25.1%** full / 17.5% Semgrep / 17.4% Snyk / 6.5% SonarQube,
> **X6 0.0% HIGH FPR** on 7 mature PyPI packages.

## Precision & Confirmed Tier
| Doc | What it covers |
|---|---|
| [CONFIRMED_TIER.md](CONFIRMED_TIER.md) | The 4-gate P4 stratum — where 96.4% precision comes from |
| [PRECISION_BENCHMARK.md](PRECISION_BENCHMARK.md) | 30-repo adversarial Layer B precision funnel |
| [PR_CURVE_ANALYSIS.md](PR_CURVE_ANALYSIS.md) | Precision-recall operating points |
| [DUAL_CORPUS_MATRIX.md](DUAL_CORPUS_MATRIX.md) | Layer A + Layer B combined view |

## Recall
| Doc | What it covers |
|---|---|
| [CVE_RECALL.md](CVE_RECALL.md) | 20-CVE pre-registered recall battery (8/8 detectable) |
| [LIVE_CVE_EVAL.md](LIVE_CVE_EVAL.md) | X1 — live-CVE blind holdout (2024–25) |
| [REALVULN_BENCHMARK.md](REALVULN_BENCHMARK.md) | RealVuln 2026 leaderboard (1,000 production CVEs) |
| [REALVULN_TRIAGE.md](REALVULN_TRIAGE.md) | Per-finding RealVuln triage |

## Head-to-Head & Competitive
| Doc | What it covers |
|---|---|
| [HEAD_TO_HEAD_BENCHMARK.md](HEAD_TO_HEAD_BENCHMARK.md) | ACR-QA vs Bandit vs Semgrep (F₁ 98.2%) |
| [COMPETITIVE_BASELINE.md](COMPETITIVE_BASELINE.md) · [COMPETITOR_COMPARISON.md](COMPETITOR_COMPARISON.md) | Tool-by-tool baselines |
| [PER_TOOL_EVALUATION.md](PER_TOOL_EVALUATION.md) | Per-tool contribution breakdown |
| [THIRD_PARTY_VALIDATION.md](THIRD_PARTY_VALIDATION.md) · [PEER_VALIDATION.md](PEER_VALIDATION.md) | External validation |

## OWASP Methodology
| Doc | What it covers |
|---|---|
| [OWASP_BENCHMARK.md](OWASP_BENCHMARK.md) | OWASP Benchmark methodology + scorecard (canonical) |
| [OWASP_BENCHMARK_allcwe_20260603.md](OWASP_BENCHMARK_allcwe_20260603.md) | Latest all-CWE run |
| [P1_BENCHMARK_METHODOLOGY.md](P1_BENCHMARK_METHODOLOGY.md) | Pre-registered P1 methodology |

## Exploit Verification & Remediation
| Doc | What it covers |
|---|---|
| [EXPLOIT_VERIFICATION.md](EXPLOIT_VERIFICATION.md) | X2 — Docker-sandbox detonation, 13 categories |
| [VERIFIED_REMEDIATION.md](VERIFIED_REMEDIATION.md) | detect → exploit → patch → re-exploit, dual-signed |

## Novel X-Track Studies
| Doc | Track |
|---|---|
| [AI_CODE_STUDY.md](AI_CODE_STUDY.md) | X3 — AI-generated code (400 samples, 4 LLMs) |
| [TIME_TRAVEL_BACKTEST.md](TIME_TRAVEL_BACKTEST.md) | X4 — time-aware predictive backtest |
| [PROTO_LLM_DETECTION.md](PROTO_LLM_DETECTION.md) | X5 — LLM-augmented detection (+5.2pp) |
| [HOLD_OUT_SPLIT.md](HOLD_OUT_SPLIT.md) | Pre-registration / hold-out discipline |

## AI Quality & Statistical Rigor
| Doc | What it covers |
|---|---|
| [HALLUCINATION_EVAL.md](HALLUCINATION_EVAL.md) | RAG hallucination reduction (RQ1) |
| [ABLATION_STUDY.md](ABLATION_STUDY.md) | Per-signal ablation |
| [DETERMINISM_PROOF.md](DETERMINISM_PROOF.md) | Deterministic pipeline proof |
| [BOOTSTRAP_CI.md](BOOTSTRAP_CI.md) | Bootstrap confidence intervals |

## User Study (RQ-supporting)
| Doc | What it covers |
|---|---|
| [USER_STUDY.md](USER_STUDY.md) · [USER_STUDY_PROTOCOL.md](USER_STUDY_PROTOCOL.md) · [USER_STUDY_RESULTS.md](USER_STUDY_RESULTS.md) · [USER_STUDY_SURVEY.md](USER_STUDY_SURVEY.md) | A/B study design, protocol, results, instrument |

## Performance, Integrity & Synthesis
| Doc | What it covers |
|---|---|
| [LOAD_TEST_RESULTS.md](LOAD_TEST_RESULTS.md) | 500 RPS sustained load test |
| [INTEGRITY.md](INTEGRITY.md) | Eval-integrity audit (`make eval-audit`) |
| [RECONCILIATION.md](RECONCILIATION.md) | Cross-run number reconciliation |
| [EVALUATION.md](EVALUATION.md) · [BENCHMARK_v5.md](BENCHMARK_v5.md) | Top-level evaluation synthesis |

---

## `snapshots/` — dated raw-run artifacts

Raw output of specific benchmark runs, retained for audit but superseded by the canonical docs
above. Not cited by the thesis. Files: OWASP/P1/P2/RealVuln/LLM-augmented runs from 2026-06-02/03.
