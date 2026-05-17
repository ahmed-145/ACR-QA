# UI Phase 3 — "One Killer Flow, Zero Fluff"

**Status:** In progress · **Started:** May 16, 2026 · **Target:** v4.6.0
**Owner:** Ahmed (KSIU thesis) · **Context:** Marketing-grade frontend for thesis defense

---

## Mission

Turn the 9-page utility dashboard into a **product showcase that markets itself**. Not by listing 25 features in a grid, but by exposing depth through ONE killer demo flow that can be filmed in 60 seconds for the thesis defense video (task 12.35).

## North Star

> A first-time visitor lands, sees ONE specific claim with proof numbers, clicks "Try Live Demo", and within 30 seconds sees seven enrichment engines firing on a single real finding from a real vulnerable repo (DVPWA). That visitor — whether it's Dr. Samy, a recruiter, or a Hacker News reader — should leave thinking "this is a real product, not a student project."

## What We're Explicitly NOT Building

- ❌ Standalone OWASP heatmap page (already an endpoint; dashboard tile is enough)
- ❌ Knowledge base browser page (66 rules in YAML; nobody browses 66 rules)
- ❌ CBoM standalone page (3 users care)
- ❌ ROI standalone page (one panel in overview)
- ❌ MCP server page (docs already cover this)
- ❌ Test Gap Analyzer page (CLI is fine)
- ❌ Multi-step scan wizard (current single-page works)
- ❌ Marimo notebook embeds (already linked)
- ❌ Documentation viewer (overengineering)
- ❌ 15-card feature grid on landing (2010 SaaS; dilutes the pitch)

Why: per the Phase 12 retrospective rule — *"If you can't say it in the thesis QA session, don't build it."* Each of the above is defendable in isolation but **diluting** in a marketing flow. Stripe/Linear/Vercel show ONE thing on their homepage. So will we.

---

## The 4 Phases

### Phase 1 — Marketing Landing (3h)

**File:** `FRONTEND/static/ui/landing.html` (new) · served at `/ui/` (replaces current login as the front door)
**Login moves to:** `/ui/login.html` (still works, just no longer the homepage)

**Layout:**
- Hero (full viewport):
  - Animated radial gradient background (purple → blue → emerald)
  - H1: *"Code review that proves it found a real bug."* (or similar — ONE concrete claim)
  - Sub: *"RAG-grounded AI · 10 static analyzers · ECDSA-signed provenance · $0 recurring cost"*
  - Two CTAs: `[▷ Try Live Demo]` (primary, gradient) + `[GitHub ↗]` (secondary)
  - Below CTAs: a looping 5-second GIF/video of the killer flow
- Proof strip (3 cards, NOT 15):
  - **97.1% precision** — *"836 real bugs detected across 4 OWASP benchmark repos"*
  - **9 / 10 OWASP Top 10** — *"with CWE mappings and Semgrep custom rules"*
  - **$0 recurring cost** — *"runs on Groq free tier · self-hosted via Docker"*
- "How it works" — 3 columns: Scan → Explain → Sign (one sentence each, no walls of text)
- "Built at KSIU" footer with GitHub stars, Railway live badge, thesis context

**Open Graph + Twitter card meta:** every page gets `<meta property="og:*">` and `<meta name="twitter:*">` so shared URLs render beautifully on social.

**Defendable claim:** *"Public marketing front door positioning ACR-QA as a product, not a script."*

---

### Phase 2 — Killer Finding Detail (4h)

**File:** `FRONTEND/static/ui/finding.html` (enhance existing)

The single most important page in the entire app. When a visitor opens a finding, they should see EVERY engine that touched it, in ONE view, without scrolling away.

**New top strip (4 chips in one row):**
1. **Confidence gauge** — circular 0–100, color-coded (red < 40, amber 40–70, green > 70)
2. **Reachability badge** — `✓ live code` (green) / `✗ dead code` (grey) / `? unknown`
3. **Exploit verdict pill** — `verified-exploitable` (red pulse) / `unexploitable` (green) / `unverified` (grey)
4. **Triage verdict** — `TP` (red) / `FP` (grey) / `needs-review` (amber) with confidence delta

**New collapsible panels (in order):**
- AI Explanation (RAG-grounded, with "cited from rule X" badge)
- **Taint Flow** — SVG diagram: source node → arrow → optional sanitizer check → sink node
- **Exploit Proof** — if verified, show the PoC payload + observed response in a code block
- **AI Triage Reasoning** — multi-step LLM reasoning trace (expandable)
- Auto-fix patch (unified diff, syntax-highlighted, copy button)
- SLSA Attestation (signature, algorithm list, verification status)

**Defendable claim:** *"Single view exposes all 7 enrichment engines simultaneously — no competitor (SonarQube, CodeRabbit) shows this depth per finding."*

---

### Phase 3 — Public Demo Mode (1h)

**Mechanism:** `?demo=1` URL param on any page bypasses auth and loads a pre-populated DVPWA run.

**Implementation:**
- JWT auth check in shared JS: if `?demo=1`, set a synthetic read-only `DEMO_TOKEN` in `sessionStorage` (not `localStorage`, ephemeral)
- Backend: new endpoint `GET /v1/demo/run` returns a fixed fixture run_id (or the latest DVPWA scan)
- Top of every page in demo mode: amber banner `"DEMO MODE — read-only sandbox · Sign up to scan your own code →"`
- All POST/DELETE buttons hidden or disabled in demo mode

**Defendable claim:** *"Zero-friction demo onboarding — visitors see the full pipeline without credentials."*

---

### Phase 4 — Smart Polish (1h)

**Visual upgrades (all pages):**
- Glassmorphism on overview/scan/runs cards: `backdrop-filter: blur(20px)` + semi-transparent bg
- Skeleton loaders for every async fetch (replace "Loading..." text)
- CSS View Transitions API for smooth page-to-page animation
- Subtle hover lifts on interactive cards (`transform: translateY(-2px)`)
- Animated badge pulse for high-severity findings

**SEO / Social:**
- Open Graph meta on every HTML page
- Twitter card meta
- Favicon set (16/32/180px + apple-touch)
- `robots.txt` allow + sitemap pointer

**Defendable claim:** *"WCAG 4.5:1 contrast preserved while adding premium product-grade aesthetic."*

---

## Schedule

| Day | Phase | Hours | Output |
|-----|-------|------:|--------|
| 1 | MD cleanup + Phase 1 landing | 3–4 | `landing.html`, OG meta, deploy-ready |
| 1 | Phase 2 finding detail | 3–4 | All 7 engines surfaced in one view |
| 2 | Phase 3 demo mode | 1–2 | `?demo=1` works end-to-end |
| 2 | Phase 4 polish + commit + push | 1–2 | Glassmorphism, transitions, social meta |

**Total: ~9 hours.** Less than half my original "show everything" plan.

## MD Cleanup (executed before Phase 1)

| File | Action | Why |
|------|--------|-----|
| `docs/ROADMAP.md` | Archive → `docs/archive/` | Mostly talks about killed Phase 2 TS rewrite |
| `docs/PHASE_12_PLAN.md` | Archive → `docs/archive/` | Phase closed (37/39 done); tactical not historical |
| `docs/INSTRUCTOR_MEETING.md` | Update in place | Has value but stale Flask/port-5000 refs |
| `docs/ai_example_eval_rce.md` | Keep | Real thesis slide material |
| `docs/setup/API-Documentation.md` | Delete | Self-marked "v2.7, archived" |
| `docs/evaluation/PERFORMANCE_BASELINE.md` | Rename → `PHASE_12_PERFORMANCE.md` | Disambiguate from `docs/PERFORMANCE_BASELINE.md` |

## Success Criteria

- [ ] First-time visitor can see the full demo flow in < 60 seconds without signing up
- [ ] Finding detail page exposes all 7 enrichment engines in one view
- [ ] Landing page shares cleanly on Twitter/LinkedIn (OG preview works)
- [ ] Demo video (12.35) can be filmed in one take using the new flow
- [ ] WCAG 2.1 AA preserved (axe-core CI still green)
- [ ] No regression in existing 9-page navigation

---

*This plan supersedes the original "Show Everything, Sell Everything" proposal after honest stress-testing against the Phase 12 retrospective's "defendable claim per task" rule.*
