# ACR-QA Dashboard

React 18 + TypeScript + Vite SPA. The frontend for the ACR-QA platform.

## Stack

| Layer | Choice |
|---|---|
| Framework | React 18 + TypeScript |
| Build | Vite 5 |
| Routing | react-router-dom v7 |
| Server state | TanStack Query v5 |
| Auth state | Zustand (persist to `localStorage["acrqa_auth"]`) |
| Styling | Tailwind CSS v3 + CSS custom properties in `src/styles/acr.css` |
| Icons | lucide-react (always `aria-hidden` on decorative use) |
| i18n | react-i18next — English + Arabic (RTL via `[dir="rtl"]` CSS) |
| Unit tests | Vitest + Testing Library (104 tests) |
| E2E tests | Playwright (55 tests) |
| Linting | ESLint + TypeScript strict |

## Quick Start

```bash
cd dashboard
npm install
npm run dev        # Vite dev server on :5174 (port may differ if :5173 is taken)
```

API calls proxy to `http://localhost:8002` via Vite config. Make sure FastAPI is running:

```bash
REDIS_PORT=6380 REDIS_HOST=localhost JWT_ACCESS_TTL_MINUTES=480 \
  .venv/bin/uvicorn FRONTEND.api.main:app --host 0.0.0.0 --port 8002
```

## Pages & Routes

| Route | Auth | Description |
|---|---|---|
| `/` | No | Landing page (redirects to `/inbox` if logged in) |
| `/login` | No | JWT login |
| `/register` | No | User registration |
| `/trust/:repoName` | No | **Public** posture page — ECDSA-verifiable badge, no login required |
| `/inbox` | Yes | Triage inbox — regressions, stale TPs, disagreements |
| `/scans` | Yes | Scan dashboard — submit new scans, view history |
| `/overview` | Yes | Security overview bento grid |
| `/findings` | Yes | All findings — search, filter by sev/category/run |
| `/vulnerabilities` | Yes | Deduplicated vulnerability list with filters |
| `/vuln/:shortId` | Yes | Vulnerability detail — history, related, chat |
| `/runs/:id` | Yes | Run detail — summary, findings, attestation, PR risk |
| `/runs/:id/compare` | Yes | Side-by-side run diff |
| `/repos` | Yes | Repository list |
| `/fleet` | Yes | Fleet posture heatmap |
| `/workbench` | Yes | Query workbench |
| `/rules` | Yes | Rules browser (327+ canonical rules) |
| `/policy` | Yes | Policy configuration viewer |
| `/cost` | Yes | Cost & ROI calculator |
| `/analytics` | Yes | Trend analytics |
| `/supply-chain` | Yes | SCA / SBOM explorer |
| `/ai-detect` | Yes | AI-generated code detector |
| `/settings` | Yes | Profile, API keys, preferences |

## Key Files

```
src/
  App.tsx                    ← Route definitions (lazy-loaded pages)
  routes/
    _layout.tsx              ← Sidebar shell — nav, theme toggle, user menu
    index.tsx                ← /scans — New Scan dialog + scan history
    inbox.tsx                ← /inbox — keyboard-driven triage (j/k/x/e/t/f/a)
    findings.tsx             ← /findings — sticky filter bar + virtualised table
    vulnerabilities.tsx      ← /vulnerabilities — deduplicated vuln list
    trust.$repoName.tsx      ← /trust/:repoName — public badge + ECDSA verify
    vuln.$shortId.tsx        ← /vuln/:id — full vulnerability detail
    runs.$id.tsx             ← /run detail with tabs
    fleet.tsx                ← fleet heatmap
    workbench.tsx            ← query workbench
  lib/
    api.ts                   ← All fetch helpers (get/post/patch) — 401 auto-logout
    auth.ts                  ← Zustand auth store + loginApi + authHeader()
    queries.ts               ← TanStack Query hooks
    sse.ts                   ← SSE EventSource for scan progress streaming
  styles/
    acr.css                  ← All custom CSS — design tokens, components, responsive
    globals.css              ← Tailwind base + CSS variables
```

## Auth Notes

- Token stored in `localStorage["acrqa_auth"]` (Zustand persist key)
- JWT access token TTL: **8 hours** (set via `JWT_ACCESS_TTL_MINUTES=480` in `.env`)
- Expired token (401) → automatic logout + redirect to `/login`
- Public routes (no auth guard): `/`, `/login`, `/register`, `/trust/:repoName`

## Tests

```bash
npm run test          # Vitest unit tests (104 tests, one-shot)
npm run test:watch    # Vitest in watch mode
npm run test:e2e      # Playwright E2E (55 tests — needs FastAPI on :8002)
npm run lint          # ESLint (0 errors expected)
npm run build         # TypeScript compile + Vite bundle (must be clean)
```

E2E tests use `mockAuth` helper (sets `localStorage["acrqa_auth"]`) and
`page.route("/v1/**", ...)` to mock the API — no live backend required.

## Sticky Layout Stack

When a page has a sticky filter bar, the z-index and `top` offsets are:

| Element | `top` | `z-index` |
|---|---|---|
| `.topbar` | `0` | `30` |
| `.sticky-filters` | `53px` | `10` |
| Column header (inside `.panel`) | `108px` | `5` |

The topbar is 53px tall (14px padding × 2 + ~25px content). The filter bar is 55px
(12px padding × 2 + 30px `inp-sm` + 1px border). Column headers must account for both.

## WCAG Notes

All text meets WCAG 2.1 AA (4.5:1 contrast ratio minimum on `#0a0a0c` background):
- `--fg-4: #909090` (4.76:1) — was `#71717a` (4.09:1, failed)
- `--fg-5: #808080` (4.09:1) — was `#52525b` (2.55:1, failed)

## Last Updated

2026-05-23 — v5.0.0b2
