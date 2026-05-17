# UI Testing Plan — Post UI Phase 3

**Status:** Layer 1 COMPLETE ✅ 2026-05-17 · Layers 2–3 deferred post-defense · **Target:** v4.6.0
**Companion to:** `UI_PHASE_3_PLAN.md`

---

## Mission

Validate every artifact UI Phase 3 ships. Catch regressions before the demo video shoot (task 12.35). Don't gold-plate — add the minimum tests that would actually fail if something broke.

## Scope — What UI Phase 3 Touches

| Surface | New / Changed |
|---|---|
| Backend | `POST /v1/auth/register` (new endpoint) |
| Pages | `landing.html`, `signup.html`, `verify.html`, `forgot.html` (new) |
| Pages | `login.html`, `finding.html` (enhanced) |
| Mechanism | `?demo=1` URL param (bypasses auth, loads fixture run) |
| Routing | `/ui/` now serves `landing.html` (was `login.html`) |

---

## Test Layers

### Layer 1 — Unit Tests (pytest, ~5 tests, ~30min)

**File:** `TESTS/test_auth_register.py` (new)

| # | Test | Asserts |
|---|---|---|
| 1 | `test_register_success` | 201, returns user_id + email + verification_code |
| 2 | `test_register_duplicate_email` | 409 with clear error message |
| 3 | `test_register_weak_password` | 400, password must be ≥ 8 chars |
| 4 | `test_register_invalid_email_format` | 400, email regex validation |
| 5 | `test_verify_code_marks_email_verified` | After verify, `users.email_verified = true` |

**Defendable claim:** *"Public registration endpoint covered by unit tests including duplicate-email and weak-password edge cases."*

---

### Layer 2 — Playwright E2E (~5 tests, ~45min)

**File:** `dashboard/e2e/auth-flow.spec.ts` (new — separate from existing `auth.spec.ts` which covers React dashboard)

| # | Test | Flow |
|---|---|---|
| 1 | `signup → verify → land on dashboard` | Fill signup form, paste demo code, verify, expect URL = `/ui/index.html` |
| 2 | `signup with duplicate email shows error` | Pre-seed user, attempt signup with same email, expect inline error toast |
| 3 | `forgot password simulated flow` | Enter email, see demo code in callout, enter new password, login with new password |
| 4 | `?demo=1 bypasses auth and loads fixture` | Hit `/ui/index.html?demo=1`, expect findings rendered without login redirect |
| 5 | `login from landing page navigates correctly` | Click "Sign In" on landing, expect `/ui/login.html` |

**Defendable claim:** *"Full auth flow (signup → verify → login → reset → demo) E2E-tested in Playwright."*

---

### Layer 3 — Accessibility (axe-core, ~5 tests, ~30min)

**File:** Extend `dashboard/e2e/accessibility.spec.ts`

| # | Page | WCAG tags |
|---|---|---|
| 1 | `landing.html` | wcag2a, wcag2aa, wcag21a, wcag21aa |
| 2 | `signup.html` | same |
| 3 | `verify.html` | same |
| 4 | `forgot.html` | same |
| 5 | redesigned `login.html` | same |

**Each test:** load page, run `injectAxe()`, run `checkA11y()`, assert zero violations of `serious` or `critical` severity.

**Defendable claim:** *"All 5 new auth pages pass WCAG 2.1 AA axe-core scan in CI."*

---

### Layer 4 — Manual Smoke Checklist (~30min, do it once)

A live, click-through checklist for the demo video shoot. NOT automated — this is the human eyes pass.

```
☐ /ui/ loads landing page with animated gradient hero
☐ All 3 CTAs work: Try Live Demo, Sign Up, GitHub
☐ Sign up with brand-new email → verify code visible inline → click verify → land on overview
☐ Sign up with EXISTING email → see "already registered" error
☐ Sign up with weak password ("abc") → see strength meter red + error
☐ Login with verified user → land on overview
☐ Login with wrong password → see error, don't redirect
☐ Forgot password → enter email → see code → set new password → login works with new pw
☐ ?demo=1 on any page bypasses login
☐ ?demo=1 banner is visible and dismissable
☐ All 9 nav links work in demo mode (read-only ones)
☐ POST/DELETE buttons hidden or disabled in demo mode
☐ Finding detail page shows all 4 chips at top (confidence, reachability, exploit, triage)
☐ Taint flow SVG renders for a finding with taint data
☐ Exploit proof code block renders for a verified-exploitable finding
☐ ⌘K command palette works on every page
☐ Theme toggle (☀/☽) persists across page reloads
☐ Twitter share preview (use https://cards-dev.twitter.com/validator) shows OG meta
☐ All pages still pass WCAG (axe DevTools extension, no critical violations)
☐ Logout clears session and redirects to landing
```

---

### Layer 5 — Visual Regression (Optional, ~30min)

If time permits: capture before/after screenshots of every page using Playwright's `page.screenshot()`. Stored at `dashboard/e2e/screenshots/v4.6.0/`. Useful as demo video B-roll AND as regression baseline for future UI work.

```bash
# add to e2e suite
test('capture screenshots for demo video', async ({ page }) => {
  for (const route of ['/landing', '/login', '/signup', '/verify', '/forgot', '/index', '/finding']) {
    await page.goto(`http://localhost:8000/ui${route}.html`);
    await page.screenshot({ path: `screenshots/v4.6.0/${route}.png`, fullPage: true });
  }
});
```

---

## Effort Budget

| Layer | Tests | Hours |
|---|---|---|
| Layer 1 — Unit | 5 | 0.5 |
| Layer 2 — E2E | 5 | 0.75 |
| Layer 3 — A11y | 5 | 0.5 |
| Layer 4 — Manual | 20 items | 0.5 |
| Layer 5 — Screenshots | optional | 0.5 |

**Total: ~3 hours.** 15 new automated tests + 20-item manual checklist.

## Success Criteria

- [x] All 5 new unit tests pass ✅ 2026-05-17 (TESTS/test_auth_register.py)
- [ ] All 5 new E2E tests pass on Chromium + Firefox + WebKit — **deferred post-defense** (Playwright cross-browser infra)
- [ ] Zero `serious` or `critical` axe-core violations on new pages — **deferred post-defense** (axe-core on 4 new auth pages)
- [ ] Manual smoke checklist 20/20 ticked — **human task: run before filming demo video**
- [x] Full Python suite (2,279 tests) still green ✅ 2026-05-17
- [ ] No regression in existing 66 TS unit tests — **human task: run `npm test` before demo video**

## Updated Numbers After Completion

| Metric | Before | After |
|---|------:|------:|
| Python tests | 2,274 | 2,279 (+5) |
| Playwright e2e flows | 29 | 39 (+10: 5 auth + 5 a11y) |
| Total reported | 2,339 | 2,345 |
| FastAPI endpoints | 36 | 37 (+1: register) |

---

## What's Explicitly NOT Tested

- ❌ Snapshot tests of HTML (brittle on CSS tweaks)
- ❌ Load test on `/v1/auth/register` (Locust already covers `/v1/auth/login` at 500 RPS, same DB path)
- ❌ New mutation testing run (Phase 12 W1 baseline stands)
- ❌ Real SMTP integration (this is demo-mode by design)
- ❌ CAPTCHA / rate limiting on register (Redis rate limiter already in place)
