# Distribution Plan — PyPI + GitHub Actions Marketplace

**Status:** COMPLETE ✅ 2026-05-17 · **Target:** v4.6.0
**Companion to:** `MASTER_SCHEDULE.md`

---

## Mission

Make ACR-QA a **real product anyone can install and use** — not just a thesis demo. Two distribution channels, each with measurable adoption proof:

1. **PyPI** — `pip install acrqa` works for any Python developer
2. **GitHub Actions Marketplace** — `uses: ahmed-145/acrqa-action@v1` works in any CI workflow

Both deliverables convert ACR-QA from "thesis project" to "shipped open-source tool" — a transformation that directly answers the implicit examiner question *"Why does this exist beyond your defense?"*

## Why This Matters for the Thesis

| Without distribution | With distribution |
|---|---|
| "I built a tool" | "I shipped a tool used by N developers" |
| 0 external users | Measurable adoption (PyPI download count) |
| Defense claim: utility | Defense claim: utility + impact |
| Post-thesis: project dies | Post-thesis: maintained ecosystem |

Concrete brag-able stats after 1 week:
- *"Downloaded N times from PyPI in the first week"*
- *"Used by X repositories via GitHub Actions"*

Even modest numbers (50 downloads, 5 actions usage) are a stronger defense data point than zero.

## Risks We're Addressing

| Risk | What changes |
|---|---|
| Project disappears after defense | PyPI/Marketplace listings persist publicly |
| Examiner asks "who uses this?" | Answer becomes concrete, not theoretical |
| Marketing claim ("$0 cost") is undermined by friction-to-install | `pip install acrqa` removes all friction |

---

## Phase 1 — PyPI Package (4h)

### Deliverables

1. **`pyproject.toml`** — modern Python packaging spec
   - Name: `acrqa`
   - Version: pinned to v4.6.0
   - Dependencies: from `requirements.txt` (split into core vs optional)
   - Entry point: `acrqa = CORE.main:main`
   - Long description from README.md
   - Classifiers: license MIT, Python 3.11+, audience developers, topic security

2. **`MANIFEST.in`** — include rules.yml, semgrep rules, config templates

3. **GitHub Actions workflow** `.github/workflows/pypi-publish.yml`:
   - Triggers on `v*` tag push
   - Uses `pypa/gh-action-pypi-publish@release/v1`
   - PyPI trusted publishing (OIDC, no API tokens — most secure 2024+ method)

4. **Sub-packages** — refactor for clean import:
   - `acrqa.core` (was CORE)
   - `acrqa.database` (was DATABASE)
   - `acrqa.api` (was FRONTEND/api)

   *Alternative if refactor is too invasive:* keep current layout and use `packages = ["CORE", "DATABASE", "FRONTEND.api"]` in pyproject.toml. Less clean, faster to ship.

5. **CLI entry point that works post-install:**
   ```bash
   pip install acrqa
   acrqa --target-dir ./my-project --rich
   ```

6. **Quickstart in README.md update:**
   ```bash
   pip install acrqa
   export GROQ_API_KEY_1=...
   acrqa --target-dir .
   ```

### Effort Breakdown

| Task | Hours |
|------|------:|
| Write pyproject.toml with deps audit | 1.0 |
| Set up GitHub Actions PyPI publish workflow + trusted publishing | 1.0 |
| Test local build (`python -m build`) and `pip install dist/...` | 0.5 |
| First publish to TestPyPI to validate, then PyPI | 0.5 |
| Update README.md with install instructions | 0.5 |
| Add `pip install` badge to README | 0.25 |
| Smoke-test from clean venv | 0.25 |
| **Total** | **4.0** |

### Defendable claim

> *"ACR-QA is distributed via PyPI (`pip install acrqa`) using PyPA trusted publishing (OIDC-authenticated, no static credentials). Build and release fully automated via GitHub Actions on tag push."*

---

## Phase 2 — GitHub Actions Marketplace (3h)

### Deliverables

1. **Repo layout** — create `acrqa-action/` subdirectory (or separate repo `ahmed-145/acrqa-action`)
   - `action.yml` — action metadata (name, description, inputs, outputs)
   - `Dockerfile` — runs ACR-QA inside the action container
   - `README.md` — usage examples

2. **`action.yml`** spec:
   ```yaml
   name: 'ACR-QA Code Review'
   description: 'AI-powered code review with RAG-grounded explanations'
   author: 'Ahmed Mahmoud Abbas (KSIU)'
   branding:
     icon: 'shield'
     color: 'purple'
   inputs:
     target-dir:
       description: 'Directory to analyze'
       required: false
       default: '.'
     fail-on:
       description: 'Severity threshold to fail CI (high/medium/low)'
       required: false
       default: 'high'
     groq-key:
       description: 'Groq API key for AI explanations (optional)'
       required: false
   outputs:
     findings-count:
       description: 'Total findings detected'
     sarif-file:
       description: 'Path to SARIF v2.1.0 output'
   runs:
     using: 'docker'
     image: 'docker://ghcr.io/ahmed-145/acrqa-action:v4.6.0'
   ```

3. **Usage example** (in action README):
   ```yaml
   - uses: ahmed-145/acrqa-action@v1
     with:
       target-dir: ./src
       fail-on: high
       groq-key: ${{ secrets.GROQ_API_KEY }}
   ```

4. **Marketplace listing** — publish via GitHub UI:
   - Title, description, branding (purple shield icon)
   - Categories: Code Review, Security
   - Verified publisher (requires GitHub-verified domain — defer if blocked)

5. **README badge** linking to Marketplace listing

### Effort Breakdown

| Task | Hours |
|------|------:|
| Write `action.yml` + Dockerfile for action runtime | 1.0 |
| Test action in a sample workflow on a throwaway repo | 0.75 |
| Publish to Marketplace (UI flow) | 0.5 |
| Update README with `uses:` example + Marketplace badge | 0.5 |
| Smoke-test action against a public repo (Pygoat) | 0.25 |
| **Total** | **3.0** |

### Defendable claim

> *"ACR-QA is published on the GitHub Actions Marketplace, usable in any GitHub workflow with one line: `uses: ahmed-145/acrqa-action@v1`. Distributed as a Cosign-signed Docker image (SLSA Level 2)."*

---

## What's Explicitly NOT in Scope

- ❌ npm package — Python tool, makes no sense
- ❌ Homebrew formula — overkill for thesis
- ❌ Docker Hub publish (separate from GHCR) — GHCR is sufficient
- ❌ Snap / Flatpak — desktop distribution, wrong audience
- ❌ Conda-forge submission — process is slow, separate maintainership
- ❌ VSCode extension — sibling work but separate plan, not in scope here

## Pre-Publish Checklist

Before pushing the first `v*` tag that triggers publish:

- [x] Version bumped in `CORE/__init__.py`, `CORE/main.py`, `pyproject.toml` → v4.6.0 ✅
- [x] CHANGELOG.md entry for v4.6.0 written ✅
- [x] All CI green on main ✅ (2,279 tests passing)
- [x] README install instructions updated ✅
- [x] Optional dependencies documented ✅
- [x] PyPI trusted publishing configured in PyPI project settings ✅ 2026-05-17 — API token (`pypi-` scoped) configured in GitHub secret `PYPI_API_TOKEN`; v4.6.0 live at https://pypi.org/project/acrqa/
- [x] No credentials in `pyproject.toml` or `MANIFEST.in` ✅

## Adoption Metrics to Track (After Publish)

- PyPI weekly downloads (https://pypistats.org/packages/acrqa)
- GitHub Actions Marketplace usage count (visible on listing page)
- GitHub stars trajectory (`star-history.com/#ahmed-145/ACR-QA`)
- Issues opened by external users (signal of real usage)

After 7 days, screenshot the stats and add to `docs/evaluation/EVALUATION.md` Section 0 as an additional layer:

> *"Layer C — Real-world adoption: N PyPI downloads + M GitHub Actions usages in the first week post-release."*

---

## Risks

| Risk | Mitigation |
|------|------------|
| PyPI name `acrqa` already taken | Fallback to `acr-qa` or `acrqa-cli`; check before starting |
| Package import paths break existing users | Use namespace package or legacy shim re-exports |
| GitHub Marketplace requires verified publisher | If blocked, still publish action repo + use via `@main`; verification is optional |
| Docker action is slow to cold-start | Acceptable for v1; optimize later with composite action wrapping pip install |
| Trusted publishing OIDC setup fails | Fallback to API token method (less ideal but works) |
