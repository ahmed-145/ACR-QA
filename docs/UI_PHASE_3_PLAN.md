# UI Phase 3 — "One Killer Flow, Zero Fluff"

**Status:** COMPLETE ✅ 2026-05-17 · **Started:** May 16, 2026 · **Shipped:** v4.6.0
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

### Phase 1 — Marketing Landing + Full Auth UX (5h)

**Files (new):** `landing.html`, `signup.html`, `verify.html`, `forgot.html`
**Files (enhance):** `login.html`
**Backend:** new `POST /v1/auth/register` endpoint (no admin auth required)
**Mounted at:** `/ui/` serves `landing.html` (replaces current login as front door)

#### 1.A Marketing Landing (`landing.html`)

- Hero (full viewport):
  - Animated radial gradient background (purple → blue → emerald)
  - H1: *"Code review that proves it found a real bug."* (or similar — ONE concrete claim)
  - Sub: *"RAG-grounded AI · 10 static analyzers · ECDSA-signed provenance · $0 recurring cost"*
  - Three CTAs: `[▷ Try Live Demo]` (gradient) + `[Sign Up Free]` + `[GitHub ↗]`
  - Below CTAs: looping 5-second GIF/video of the killer flow
- Proof strip (3 cards, NOT 15):
  - **97.1% precision** — *"836 real bugs detected across 4 OWASP benchmark repos"*
  - **9 / 10 OWASP Top 10** — *"with CWE mappings and Semgrep custom rules"*
  - **$0 recurring cost** — *"runs on Groq free tier · self-hosted via Docker"*
- "How it works" — 3 columns: Scan → Explain → Sign (one sentence each)
- "Built at KSIU" footer with GitHub stars, Railway live badge, thesis context

#### 1.B Sign Up (`signup.html`)

- Email input with live validation (regex + duplicate check via API)
- Password input with **strength meter** (length + char classes + entropy)
- Confirm password (must match)
- Optional "I agree to terms" checkbox
- POSTs to new `/v1/auth/register` → redirect to `verify.html?email=...`

#### 1.C Email Verification (`verify.html`)

**Demo-mode simulation** — no SMTP infrastructure needed:
- 6-digit code input (auto-tab between fields)
- After signup, the code is shown inline in an amber "Demo mode" callout:
  *"In production this would be emailed. For demo, your code is: `483921`"*
- "Resend code" link (regenerates the simulated code)
- Verify button → marks user as verified → auto-login → redirect to overview

#### 1.D Login (`login.html` — redesigned)

- Glass-card centered on dark gradient
- Email + password, password reveal toggle
- "Remember me" checkbox (extends refresh token to 30d)
- "Forgot password?" link
- "Don't have an account? Sign up" link
- Same JWT flow as today (no breaking changes)

#### 1.E Forgot Password (`forgot.html` — simulated)

- Email input
- After submit: same "demo mode" callout shows the reset link/code in-UI
- Two-step: enter code → set new password → auto-login

#### 1.F New backend endpoint

```python
POST /v1/auth/register
body: { email, password }
response 201: { user_id, email, verification_code }  # code shown in UI for demo
response 409: email already exists
```

- Validates email format, password ≥ 8 chars
- Inserts into `users` table with `role='member'`, `email_verified=False`, `verification_code=<6 digits>`
- Returns the code in response (DEMO MODE — would be emailed in production)

#### Open Graph + Twitter card meta

Every page gets `<meta property="og:*">` and `<meta name="twitter:*">` so shared URLs render beautifully on social.

**Defendable claim:** *"Production-grade auth UX (signup → verify → login → recovery) with honest demo-mode disclosure for email simulation."*

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
| 1 | MD cleanup ✅ + Phase 1 landing + auth UX | 5 | `landing.html`, `signup.html`, `verify.html`, `forgot.html`, redesigned `login.html`, `POST /v1/auth/register` |
| 1 | Phase 2 killer finding detail | 4 | All 7 engines surfaced in one view |
| 2 | Phase 3 demo mode | 1 | `?demo=1` works end-to-end |
| 2 | Phase 4 polish + commit + push | 1 | Glassmorphism, transitions, OG meta on every page |

**Total: ~11 hours.** Still half my original "show everything" plan; bigger than v1 of this plan because real auth UX (signup → verify → login → reset) is non-negotiable for a marketing-grade product.

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

- [x] First-time visitor lands on `/ui/` and sees a marketing page (not login) ✅ 2026-05-17
- [x] Visitor can click "Try Live Demo" and see findings in < 30s without auth ✅ 2026-05-17 (demo mode endpoint + seeded findings)
- [x] Visitor can sign up → verify (demo code) → land in dashboard in < 60s ✅ 2026-05-17 (register + verify flow + JWT redirect)
- [x] Login, signup, verify, forgot-password all work end-to-end ✅ 2026-05-17 (4 auth pages shipped + 2,279 tests green)
- [x] Finding detail page exposes all 7 enrichment engines in one view ✅ 2026-05-17 (finding-detail.html)
- [x] Landing page shares cleanly on Twitter/LinkedIn (OG preview works) ✅ 2026-05-17 (OG meta tags in landing page)
- [ ] Demo video (12.35) can be filmed in one take using the new flow — **human task: film after defense prep**
- [x] WCAG 2.1 AA preserved (axe-core CI still green) ✅ 2026-05-17
- [x] No regression in existing 9-page navigation ✅ 2026-05-17 (CI green, 66 TS tests pass)

---

*This plan supersedes the original "Show Everything, Sell Everything" proposal after honest stress-testing against the Phase 12 retrospective's "defendable claim per task" rule.*
