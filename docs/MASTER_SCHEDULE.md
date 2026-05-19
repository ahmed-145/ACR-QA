# Master Schedule — Thesis Defense Runway

**Status:** v4.6.0 ✅ COMPLETE 2026-05-17. **Now superseded by [`GOD_MODE_V3_PLAN.md`](GOD_MODE_V3_PLAN.md) — the active 6-week Phase A + 12-week Phase B + 24-week Phase C plan toward v5.0.0 and post-defense launch.**
**Defense runway:** ~May 19 — June 25, 2026
**Target tag:** v5.0.0 (Phase A complete; tag post-defense)
**Active progress (v5.0.0-beta):** Phase A Weeks 1 ✅ + 2 ✅ + 3 ✅ + 4 ✅ shipped on `main`. Tests **2,561**. Endpoints **47**. Migrations **15**. Ground-truth YAMLs **23** (CVE recall battery **20** pre-registered).

---

## Why this doc exists

Five plan MDs (UI Phase 3, UI Testing, Eval Bulletproofing, Distribution, plus the existing PRESENTATION_SCRIPT) each describe what to build. This doc says **when** and **in what order**. It exists because:

- Without a master schedule, plans get executed in random order and dependencies break
- Critical-path work (CVE pilot) gets buried by lower-priority work (glassmorphism polish)
- A 4-week runway is plenty, but only if we don't waste it building things in the wrong order

## Sequencing Principle

**Risk-first, then ship, then polish:**

1. **Risk-first** — Tier 0 + CVE pilot in W1. If CVE recall disappoints, we have 3 weeks to pivot defense narrative.
2. **Ship** — Lock in eval numbers (W2) before UI (W3–W4). Better to have boring UI + strong eval than beautiful UI + weak eval.
3. **Polish** — Demo video and final commits in W5.

## The 5-Week Plan

### Week 1 (~10h) — Risk-First Eval
| Day | Task | Hours | Source plan |
|-----|------|------:|-------------|
| Mon | Tier 0 integrity infrastructure | 3 | EVAL_BULLETPROOFING |
| Mon | CVE pilot — 5 CVEs only | 2 | EVAL_BULLETPROOFING (Tier 1) |
| Tue | **Decision gate:** review pilot results | 0.5 | — |
| Tue–Fri | Start Tier 1 full (~5h of 15h) | 5 | EVAL_BULLETPROOFING (Tier 1) |

**Decision gate criteria:**
- Pilot recall > 60% → commit to full Tier 1
- Pilot recall 30–60% → continue Tier 1 but lead defense with FP rate
- Pilot recall < 30% → pivot: skip full CVE table, lean entirely on FP rate + corpus diversity

### Week 2 (~13h) — Lock In Eval Numbers
| Task | Hours | Source plan |
|------|------:|-------------|
| Finish Tier 1 CVE recall (full 15–20 CVEs) | 10 | EVAL_BULLETPROOFING (Tier 1) |
| Start Tier 3 corpus expansion (govwa + 1 repo) | 2 | EVAL_BULLETPROOFING (Tier 3) |
| **One-command run validation** — `make up && make db-migrate && make seed-admin` on a clean venv; fix any README gaps found | 1 | Gap 5 — GOD_MODE_PLAN §7 item 1 |

### Week 3 (~12h) — Finish Eval, Start UI
| Task | Hours | Source plan |
|------|------:|-------------|
| Finish Tier 3 corpus expansion (Django + FastAPI + TS) | 6 | EVAL_BULLETPROOFING (Tier 3) |
| UI Phase 1: landing + auth UX (signup/verify/forgot/login) | 6 | UI_PHASE_3 |

### Week 4 (~19h) — Polish + Validation + Docs
| Task | Hours | Source plan |
|------|------:|-------------|
| UI Phase 2: killer finding detail page | 4 | UI_PHASE_3 |
| UI Phase 3: demo mode (`?demo=1`) | 1 | UI_PHASE_3 |
| UI Phase 4: smart polish | 1 | UI_PHASE_3 |
| UI testing: 5 unit + 5 E2E + 5 a11y + manual checklist | 3 | UI_TESTING |
| **Snapshot tests** — `TESTS/snapshot/test_snapshot_dsvw.py` + `test_snapshot_dvpwa.py`; commit expected JSON; wire into CI (slow marker) | 2 | Gap 6 — GOD_MODE_PLAN §9.3.4 |
| Tier 2 peer validation (κ on 20-finding sample) | 3 | EVAL_BULLETPROOFING (Tier 2) |
| Update EVALUATION.md with final numbers | 2 | EVAL_BULLETPROOFING |
| **Documentation sweep** — audit every MD in `docs/` for stale numbers, versions, endpoints, test counts; update all before W5 | 3 | Gap 4 pre-req + thesis hygiene |

### Week 5 (~14h) — Distribution + Demo Video
| Task | Hours | Source plan |
|------|------:|-------------|
| **Bump version** — `CORE/__init__.py`, `CORE/main.py`, `pyproject.toml` → v4.6.0; write `CHANGELOG.md` v4.6.0 entry | 1 | Gap 4 — DISTRIBUTION_PLAN pre-publish checklist |
| PyPI release (`pip install acrqa`) | 4 | DISTRIBUTION |
| GitHub Actions Marketplace listing | 3 | DISTRIBUTION |
| **Tag v4.6.0** — `git tag v4.6.0 && git push origin v4.6.0` (triggers PyPI OIDC publish) | 0.5 | Gap 4 — explicit release step |
| Demo video filming (5 min, OBS) | 3 | task 12.35 |
| YouTube upload + final commits | 1 | task 12.36 |
| **Final MD audit pass** — re-run `scripts/audit_eval_numbers.py`; confirm all docs reflect v4.6.0 numbers and the tagged release | 1.5 | Gap 4 + documentation sweep sign-off |

---

## Totals

| | Hours |
|---|------:|
| Eval Bulletproofing (Tiers 0–3) | 29 |
| UI Phase 3 (all 4 sub-phases) | 12 |
| UI Testing | 3 |
| Snapshot tests (Layer 4) | 2 |
| One-command run validation | 1 |
| Documentation sweep (W4 + W5 final audit) | 4.5 |
| Distribution (PyPI + Marketplace + tag) | 8.5 |
| Demo video + YouTube | 4 |
| **Grand total** | **~64** |

Spread over 5 weeks = ~13h/week. Still realistic — W4 is the heavy week at ~19h.

---

## Cuts From Original Plans (To Avoid Scope Creep)

| Cut | Why |
|-----|-----|
| Multi-step scan wizard | Current single-page works |
| Marimo notebook updates | Already linked, low marginal value |
| Standalone OWASP heatmap page | Existing endpoint is enough |
| Knowledge base browser page | Nobody browses 66 rules |
| CBoM standalone page | 3 users care |
| Test Gap Analyzer page | CLI is fine |
| Documentation viewer in UI | Overengineering |

## Plan Document Map

| Plan | What it covers | Weeks |
|------|----------------|------:|
| `EVAL_EXPANSION_PLAN.md` | Tier 0 integrity + Tier 1 CVE recall + Tier 2 peer κ + Tier 3 corpus | W1–W4 |
| `UI_PHASE_3_PLAN.md` | Landing + auth UX + killer finding detail + demo mode + polish | W3–W4 |
| `UI_TESTING_PLAN.md` | 15 automated tests + 20-item manual checklist | W4 |
| `DISTRIBUTION_PLAN.md` | PyPI release + GitHub Actions Marketplace listing | W5 |
| `evaluation/INTEGRITY.md` | Charter for evaluation honesty (Tier 0 deliverable) | W1 |
| `PRESENTATION_SCRIPT.md` | Verbal defense + Q&A cheat sheet | Updated W4 |
| `DEMO_VIDEO_SCRIPT.md` | 5-minute filming script (task 12.35) | W5 |

---

## Risk Register

| Risk | Probability | Mitigation |
|------|:-----------:|------------|
| CVE pilot shows weak recall (<30%) | Medium | Decision gate at end of W1; pivot to FP-rate-led defense |
| Peer reviewers unavailable | Medium | Fallback to 1 reviewer + author, document as limitation |
| Demo video filming takes multiple takes | Medium | Budget 6h for filming if 3h insufficient |
| Real production bugs surface during eval | Low | Treat as win — bugs found in eval are bugs fixed in product |
| Scope creep adds new "must-haves" | High | This doc is the contract — defer all additions to post-defense |
| Defense moves earlier than expected | Low | Tier 0 + Tier 1 + Week 5 (demo video) is the minimum shippable; everything else defers |

## Weekly Check-in Format

End of each week, update this doc with:
- ✅ What got done
- ⚠️ What slipped and why
- 🔄 What changed in next week's plan as a result

This is the lived-in version of the plan, not the aspirational one.

---

## Success Criteria (End of W5)

- [x] Tier 0 integrity infrastructure in place; `make eval-reproduce` works ✅ 2026-05-17
- [x] `make eval-audit` runs and passes 17/17 claims ✅ 2026-05-17
- [x] Tier 1 CVE recall table published in `docs/evaluation/CVE_RECALL.md` ✅ 2026-05-17 (2/10=20%)
- [x] Tier 2 peer validation κ documented in `docs/evaluation/PEER_VALIDATION.md` ✅ 2026-05-17 (κ=0.74)
- [x] Tier 3 corpus expanded — 13 repos across 4 languages (GoVWA, vulnerable-node, django.nV added) ✅ 2026-05-17
- [x] UI Phase 3 shipped — landing + auth UX (signup/verify/forgot/login) + killer finding detail + demo mode ✅ 2026-05-17
- [x] UI Testing Layer 1 — 5 unit tests for register/verify (all passing) ✅ 2026-05-17
- [x] Snapshot tests committed + wired into CI (DSVW + DVPWA, @pytest.mark.slow) ✅ 2026-05-17
- [x] `make up && make db-migrate && make seed-admin` works on a clean venv ✅ W2
- [x] PyPI package — `pyproject.toml [project]` section + `pypi-publish.yml` OIDC workflow ✅ 2026-05-17
- [x] GitHub Actions Marketplace — `acrqa-action/action.yml` + Dockerfile + entrypoint ✅ 2026-05-17
- [x] v4.6.0 — version bumped in `CORE/__init__.py`, `CORE/main.py`; CHANGELOG.md entry written ✅ 2026-05-17
- [ ] Demo video uploaded to YouTube (human task — film with OBS, upload)
- [x] PRESENTATION_SCRIPT.md verbal pivots updated with new numbers ✅ 2026-05-17
- [x] All MDs audited — v4.6.0 versions propagated; EVALUATION.md sections 3b+3c added ✅ 2026-05-17
