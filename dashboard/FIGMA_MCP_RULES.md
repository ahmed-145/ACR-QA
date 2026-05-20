# Figma MCP Integration Rules — ACR-QA Dashboard

> For use by AI agents (Claude Code + Figma MCP) when generating or syncing Figma designs from this codebase.

---

## 1. Design Tokens

**All tokens are CSS custom properties defined in `src/styles/globals.css` and consumed via Tailwind.**

### Color tokens (HSL, no `hsl()` wrapper in the variable itself)

```css
/* Light mode (:root) */
--background:             0 0% 100%
--foreground:             222.2 84% 4.9%
--card:                   0 0% 100%
--card-foreground:        222.2 84% 4.9%
--border:                 214.3 31.8% 91.4%
--input:                  214.3 31.8% 91.4%
--primary:                222.2 47.4% 11.2%       /* dark navy */
--primary-foreground:     210 40% 98%             /* near-white */
--secondary:              210 40% 96.1%           /* light grey */
--secondary-foreground:   222.2 47.4% 11.2%
--muted:                  210 40% 96.1%
--muted-foreground:       215.4 16.3% 46.9%       /* mid-grey text */
--accent:                 210 40% 96.1%
--accent-foreground:      222.2 47.4% 11.2%
--destructive:            0 72.2% 40.8%           /* red */
--destructive-foreground: 210 40% 98%
--ring:                   222.2 84% 4.9%
--radius:                 0.5rem
```

```css
/* Dark mode (.dark) */
--background:             222.2 84% 4.9%
--foreground:             210 40% 98%
--border:                 217.2 32.6% 17.5%
--primary:                210 40% 98%
--primary-foreground:     222.2 47.4% 11.2%
--muted-foreground:       215 20.2% 65.1%
--destructive:            0 62.8% 30.6%
--ring:                   212.7 26.8% 83.9%
```

### Semantic severity colours (utility classes, not tokens)

These are inline Tailwind — they do **not** map to CSS variables. Use them exactly as-is in Figma frames:

| Severity | Background | Text |
|----------|-----------|------|
| HIGH / CRITICAL | `bg-red-100` `#fee2e2` | `text-red-800` `#991b1b` |
| MEDIUM | `bg-yellow-100` `#fef9c3` | `text-yellow-800` `#854d0e` |
| LOW | `bg-blue-100` `#dbeafe` | `text-blue-700` `#1d4ed8` |
| INFO / default | `bg-gray-100` `#f3f4f6` | `text-gray-700` `#374151` |

Status colours (scan run state):

| Status | Background | Text |
|--------|-----------|------|
| completed | `bg-green-100` | `text-green-800` |
| running | `bg-blue-100` | `text-blue-800` |
| failed | `bg-red-100` | `text-red-800` |
| pending | `bg-gray-100` | `text-gray-700` |

### Border radius

```
--radius: 0.5rem (8px)   → Tailwind: rounded-md
calc(--radius - 2px): 6px → Tailwind: rounded-sm
--radius + extra: 12px    → Tailwind: rounded-xl   (Card outer wrapper uses this)
```

---

## 2. Typography

No custom font — uses system sans-serif (Tailwind default: `font-sans`). No `@font-face`. Text sizes via standard Tailwind scale:

| Use | Class | Size |
|-----|-------|------|
| Card title | `text-base font-semibold` | 16px/600 |
| Body / badge | `text-sm` | 14px |
| Caption / labels | `text-xs` | 12px |
| Nav links | `text-sm font-medium` | 14px/500 |

---

## 3. Component Library

All primitives live in `dashboard/src/components/ui/`. They use the **shadcn/ui** pattern: hand-written, no shadcn CLI dependency — just `cva` + `clsx` + `tailwind-merge`.

### Pattern: every primitive

```ts
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const xVariants = cva("<base-classes>", { variants: { ... }, defaultVariants: { ... } });

export interface XProps extends HTMLAttributes<HTMLElement>, VariantProps<typeof xVariants> {}
export function X({ className, variant, ...props }: XProps) {
  return <div className={cn(xVariants({ variant }), className)} {...props} />;
}
```

### Primitive inventory

| File | Exports | Variants |
|------|---------|----------|
| `ui/button.tsx` | `Button`, `buttonVariants` | `default`, `destructive`, `outline`, `secondary`, `ghost`, `link` × sizes `default`, `sm`, `lg`, `icon` |
| `ui/badge.tsx` | `Badge`, `badgeVariants` | `default`, `secondary`, `destructive`, `outline`, `high`, `medium`, `low` |
| `ui/card.tsx` | `Card`, `CardHeader`, `CardTitle`, `CardContent`, `CardFooter` | no variants — classes only |
| `ui/input.tsx` | `Input` | no variants |
| `ui/dialog.tsx` | `Dialog`, `DialogContent`, `DialogHeader`, `DialogTitle`, `DialogDescription` | no variants |
| `ui/skeleton.tsx` | `Skeleton`, `SkeletonCard`, `SkeletonTable` | className prop only |
| `ui/badge.tsx` | `Badge` | see above |
| `ui/toast.tsx` | `Toast`, `useToast` | — |
| `ui/error-boundary.tsx` | `ErrorBoundary` | — |
| `ui/command-palette.tsx` | `CommandPalette` | — |

### Feature components

```
components/
├── findings/
│   ├── FindingsTable.tsx    — main data table (sortable, filterable)
│   ├── FindingModal.tsx     — full finding detail sheet
│   ├── ReasoningChain.tsx   — AI step-by-step explanation
│   ├── ExploitProofPanel.tsx
│   ├── AutofixDiff.tsx      — react-diff-viewer-continued
│   └── TaintFlowGraph.tsx
├── scans/
│   ├── ScanCard.tsx         — card per run in list view
│   ├── ScanProgress.tsx     — SSE-driven live progress bar
│   └── TrendChart.tsx       — Recharts line chart
├── compliance/
│   └── OwaspHeatmap.tsx
├── supply/
│   ├── DependencyTree.tsx
│   └── SbomDownload.tsx
└── mode/
    └── ModeBadge.tsx        — demo/live mode indicator
```

---

## 4. Frameworks & Libraries

| Layer | Choice | Version |
|-------|--------|---------|
| UI framework | React | 18.3 |
| Routing | react-router-dom | v7 |
| Server state | @tanstack/react-query | v5 |
| Client state | zustand | v5 |
| Charts | recharts | v3 |
| Icons | lucide-react | v1.16 |
| i18n | react-i18next + i18next | v17/v26 |
| Styling | Tailwind CSS | v3.4 |
| Class util | clsx + tailwind-merge | — |
| Variant API | class-variance-authority | v0.7 |
| Build | Vite | v5 |
| Language | TypeScript | 5.6 |
| Unit tests | Vitest + @testing-library/react | — |
| E2E tests | Playwright + axe-core | — |

---

## 5. Styling Approach

- **No CSS Modules, no Styled Components, no Emotion.** Pure Tailwind utility classes.
- `cn()` in `src/lib/utils.ts` is the single composition helper: `twMerge(clsx(...inputs))`.
- Variants defined with `cva` — never raw ternaries for multi-variant components.
- Global styles only in `src/styles/globals.css` (token definitions, print, RTL overrides, `:focus-visible`).
- `src/index.css` is the Tailwind entry point (`@tailwind base/components/utilities`).
- Dark mode: class-based (`darkMode: ["class"]` in `tailwind.config.js`). Toggle via `document.documentElement.classList.toggle("dark", dark)`.

### RTL overrides (Arabic)

Applied via attribute selector in `globals.css`:

```css
[dir="rtl"] .ml-auto { margin-left: unset; margin-right: auto; }
[dir="rtl"] .ml-4    { margin-left: unset; margin-right: 1rem; }
[dir="rtl"] .mr-1    { margin-right: unset; margin-left: 0.25rem; }
[dir="rtl"] .mr-2    { margin-right: unset; margin-left: 0.5rem; }
```

### Print / PDF export

```css
@media print {
  header, nav, .no-print, button:not(.print-include) { display: none !important; }
  body { background: white !important; color: black !important; font-size: 11pt; }
  @page { margin: 1.5cm; }
}
```

---

## 6. Layout & Responsive Design

Single breakpoint pattern — mobile-first, one `md:` jump:

```tsx
/* Header height */
<header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur">
  <div className="flex h-14 items-center gap-4 px-4 md:px-6">

/* Main content */
<main className="flex-1 px-4 py-6 md:px-6 md:py-8">
```

Mobile (< 768px):
- Nav labels hidden: `hidden sm:inline`
- Email hidden: `hidden md:inline`
- Logo text hidden: `hidden md:inline`
- Min supported width: **375px**

Grid pattern for scan cards (index route):

```tsx
<div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
  {runs.map(r => <ScanCard key={r.id} run={r} />)}
</div>
```

---

## 7. Icon System

**Library:** `lucide-react` v1.16 — all icons are React components.

**Usage pattern:**

```tsx
import { Shield, LayoutDashboard, GitBranch, AlertTriangle, Clock } from "lucide-react";

<Shield className="h-5 w-5 text-primary" aria-hidden />
<GitBranch className="h-4 w-4 text-muted-foreground" />
```

**Sizing conventions:**

| Context | Class |
|---------|-------|
| Nav bar brand icon | `h-5 w-5` |
| Nav item icons | `h-4 w-4` |
| Inline body icons | `h-3 w-3` |
| Button icon-only | `h-4 w-4` |

Always add `aria-hidden` on decorative icons. Never add `aria-hidden` on icons that convey meaning without adjacent text.

No SVG sprite system — icons are tree-shaken at build time by Vite.

---

## 8. Asset Management

- One static asset: `src/assets/react.svg` (Vite default, not used in production UI).
- No image assets in the product UI — all visuals are icon-based or data-driven (charts).
- No CDN configured. Assets bundled by Vite and served from the same origin.
- Vite handles hashing and optimization at build time.

---

## 9. Project Structure

```
dashboard/
├── src/
│   ├── components/
│   │   ├── ui/              ← primitives (shadcn-style)
│   │   ├── findings/        ← finding detail UI
│   │   ├── scans/           ← scan list + progress
│   │   ├── compliance/      ← OWASP heatmap
│   │   ├── supply/          ← dependency tree + SBOM
│   │   └── mode/            ← demo/live badge
│   ├── routes/
│   │   ├── _layout.tsx      ← shell (header + nav + <Outlet>)
│   │   ├── index.tsx        ← /  (scan list)
│   │   ├── runs.$id.tsx     ← /runs/:id
│   │   ├── runs.$id.compare.tsx
│   │   ├── supply-chain.tsx ← /supply-chain
│   │   ├── settings.tsx     ← /settings
│   │   └── auth.login.tsx   ← /login
│   ├── lib/
│   │   ├── api.ts           ← typed fetch wrappers + Run/Finding types
│   │   ├── auth.ts          ← zustand auth store
│   │   ├── queries.ts       ← react-query query/mutation definitions
│   │   ├── utils.ts         ← cn(), severityColor(), riskColor(), formatDate(), truncate()
│   │   ├── i18n.ts          ← i18next setup + setLanguage()
│   │   └── sse.ts           ← EventSource wrapper for live progress
│   ├── locales/
│   │   ├── en.json          ← English strings
│   │   └── ar.json          ← Arabic strings
│   ├── styles/
│   │   └── globals.css      ← CSS token definitions + RTL + print
│   └── test/                ← Vitest component tests
├── e2e/                     ← Playwright tests (a11y, auth, dashboard)
├── tailwind.config.js
├── vite.config.ts
└── package.json
```

---

## 10. i18n / Accessibility Notes for Figma

- **Two locales:** `en` (LTR) and `ar` (RTL). Figma frames should be designed in LTR first; a mirrored RTL variant is needed for Arabic.
- **WCAG 2.1 AA** is enforced via axe-core in CI. All interactive elements must have visible focus rings (2px solid `--ring` with 2px offset) and accessible labels.
- Colour contrast: primary (`#0f172a`) on background (`#ffffff`) = 18.4:1 — passes AAA. Muted foreground on background ≈ 4.6:1 — passes AA.
- Minimum tap target: 36×36px (`h-9 w-9` = 36px icon buttons).

---

## 11. Rules for Figma MCP Agent

1. **Match CSS tokens exactly.** Use the HSL values above for Figma color styles — do not guess hex equivalents.
2. **No custom fonts.** Use Inter or system-ui in Figma to approximate the browser default stack.
3. **Border radius:** 8px (cards get 12px outer). Keep consistent with `--radius`.
4. **Icons:** use Lucide icon set in Figma (available as community plugin "Lucide Icons"). Do not substitute with Material or Heroicons.
5. **Dark mode:** create a separate component set or mode variable for the `.dark` token values.
6. **Component naming:** mirror the code names — `Button/Default`, `Button/Destructive`, `Badge/High`, `Badge/Medium`, etc.
7. **Spacing:** Tailwind's 4px grid (`gap-4` = 16px, `px-4` = 16px, `py-6` = 24px). Stick to multiples of 4px.
8. **No Storybook** exists — use code files in `src/components/ui/` as the source of truth for variants.
9. **Severity badge colours** are Tailwind utility colours, not CSS variables. Hard-code them in Figma as fill styles.
10. **RTL:** design text-heavy frames with auto-layout direction that can be flipped. Use Figma's text direction property for Arabic frames.
