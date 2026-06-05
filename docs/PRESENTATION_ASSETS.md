# ACR-QA — Presentation Assets (Defense Day June 25, 2026)

> All figures in `docs/presentation_assets/` are **300 DPI PNG**, generated from
> real verified data by `ACR-QA-Book/figures/generate_eval_figures.py`.
> Regenerate at any time: `cd ACR-QA-Book/figures && python3 generate_eval_figures.py`

---

## Evaluation Figures (Chapter 5 — Chapter Evaluation & Testing)

### 1. `CONFUSION_MATRIX.png` — Binary Classification Result
**Use when:** Opening your evaluation section / answering "how accurate is it?"
- Left panel: 2×2 confusion matrix (SecurityEval 89+89 corpus)
  - TP=81, FN=8, FP=67, TN=22
- Right panel: derived metrics bar chart (TPR, F₃, MCC, Youden J, FPR…)
- **Key numbers to say:** "91% recall, F₃=0.854, Youden J=0.157 — best of all tools evaluated"
- The high FPR is expected — SecurityEval clean snippets are adversarially designed

---

### 2. `PR_OPERATING_POINTS.png` — Precision-Recall Space
**Use when:** Explaining the precision/recall trade-off visually
- 6 operating points scattered on a P-R plot with iso-F₁ curves
- ACR-QA Full Output (high recall, lower precision) vs Confirmed Tier (high precision)
- **Key message:** Every ACR-QA mode dominates Bandit and Semgrep on the P-R plane

---

### 3. `REALVULN_LEADERBOARD.png` — Third-Party Benchmark
**Use when:** Defending against "why not just use Bandit/Semgrep/Snyk?"
- 6 tools ranked by full-corpus recall on RealVuln 2026 (arXiv:2604.13764)
- ACR-QA+LLM: 32.4% — ACR-QA baseline: 25.1% — Snyk: 17.4% — SonarQube: 6.5%
- **Key message:** ACR-QA leads on a third-party ground truth benchmark you didn't control

---

### 4. `METRICS_TABLE.png` — Full Metrics Comparison Table
**Use when:** Committee asks for a complete side-by-side numbers table
- 8 rows: ACR-QA (4 modes) + Bandit + Semgrep + Snyk + SonarQube
- Columns: Corpus, Precision, TPR, F₁, F₃, MCC, Youden J, CVE Recall
- **Best as a backup slide** — too dense for the main deck, perfect for Q&A

---

### 5. `FUNNEL_SLIDE.png` — The Precision Funnel
**Use when:** Explaining HOW the system achieves 96.4% precision
- 6 rungs from 1,942 raw findings → 55 Confirmed Tier findings
- Every rung preserves 8/8 CVE recall (100%)
- **Key message:** Precision goes from 8.6% → 96.4% with zero CVE loss — the multi-layer architecture works

---

### 6. `HEAD_TO_HEAD.png` — Tool Benchmark Bar Chart
**Use when:** Direct comparison slide — strongest visual for the defense
- 5 tool configurations × 3 metrics (Precision, CVE Recall, F₁)
- ACR-QA P4: 96% precision, 100% CVE recall, **F₁=98.2%** — +52pp over next best
- **This is your money slide** — put it right before the conclusion

---

### 7. `CONFIDENCE_SCORING.png` — Five-Signal Diagram
**Use when:** Explaining the scoring architecture (RQ3)
- Flow diagram: 5 signals → weighted sum → Cₛ [0–100] → threshold bands
- Shows it's **label-free** — no training data needed
- **Key message:** Novel contribution — no existing SAST tool does this

---

### 8. `TEST_PYRAMID.png` — Testing Architecture
**Use when:** Answering "how did you verify your system?"
- 4 layers: Unit (∼1,933) → Integration (∼667) → TypeScript/Vitest (104) → E2E Playwright (55)
- 2,805 Python tests passing, 83.60% coverage, 14 axe-core accessibility tests
- **Key message:** This is production-grade quality, not a student prototype

---

## Architecture Figures (pre-existing, from Book)

| File | What it shows |
|------|---------------|
| `arch_overview.png` | Full system architecture |
| `pipeline_stages.png` | 5-stage pipeline (raw → confirmed) |
| `pipeline_orchestrator.png` | Orchestrator class diagram |
| `scan_flow.png` | End-to-end scan user flow |
| `er_diagram.png` | Database schema |
| `docker_stack.png` | Docker Compose services |
| `finding_lifecycle.png` | Finding state machine |
| `rag_engine.png` | RAG enrichment engine |

---

## Suggested Defense Slide Order

```
1. Title + Problem Statement
2. arch_overview.png          — system at a glance
3. pipeline_stages.png        — how it works
4. CONFUSION_MATRIX.png       — evaluation: what the numbers mean
5. FUNNEL_SLIDE.png           — how precision is achieved
6. HEAD_TO_HEAD.png           — comparison with Bandit/Semgrep (money slide)
7. REALVULN_LEADERBOARD.png   — third-party validation
8. CONFIDENCE_SCORING.png     — novel RQ3 contribution
9. TEST_PYRAMID.png           — quality assurance
10. Conclusion + Future Work
```

---

## Key Numbers to Memorize

| Metric | Value | Context |
|--------|-------|---------|
| Confirmed Tier Precision | **96.4%** | 30-repo adversarial corpus |
| CVE Recall | **100% (8/8)** | All strata, all tiers |
| F₁ at Confirmed Tier | **98.2%** | vs Bandit 21.8%, Semgrep 45.7% |
| SecurityEval TPR | **91.0%** | 89 vulnerable snippets |
| F₃ (recall-heavy) | **0.854** | Key SAST metric (recall >4× precision weight) |
| Youden J | **0.157** | Best of all 3 tools (Bandit 0.090, Semgrep 0.056) |
| MCC | **0.210** | Balanced, dataset-size independent |
| RealVuln Recall | **25.1%** | Third-party ground truth (arXiv:2604.13764) |
| RealVuln + LLM | **32.4%** | +7.3pp gain with augmentation |
| Test Count | **2,805** passing | + 104 Vitest + 55 Playwright + 14 axe |
| Coverage | **83.60%** | CORE module (CI gate: 82%) |
| Load Test | **500 RPS** | p50<40ms, p95<120ms, error<0.01% |

---

## Data Source
All numbers derived from `docs/ACTIVE_ROADMAP.md` (verified 2026-06-05).
External benchmark: arXiv:2604.13764 (RealVuln 2026, verified June 2026).
Script: `ACR-QA-Book/figures/generate_eval_figures.py`
