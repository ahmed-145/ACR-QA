# ACR-QA v3.1.3 Architecture

## System Overview

ACR-QA is a modular, pipeline-based system for automated code review with RAG-enhanced AI explanations. It runs 7 static analysis tools, normalizes all findings into a canonical schema, generates evidence-grounded explanations, and enforces configurable quality gates.

## Pipeline Stages

```
Source Code
    │
    ▼
[0] Rate Limit Check          ← Redis-backed token bucket (1 req/repo/min)
    │
    ▼
[1] DB Run Created            ← PostgreSQL analysis_runs row
    │
    ▼
[2a] Tool Detection           ← Ruff, Semgrep, Bandit, Vulture, Radon, jscpd
    │
    ▼
[2b] Extra Scanners           ← Secrets Detector, SCA Scanner (deps)
    │
    ▼
[3a] Normalization            ← tool outputs → canonical schema (normalizer.py)
[3b] Config Filtering         ← .acrqa.yml: disabled rules, ignored paths, min severity
[3c] Deduplication            ← 2-pass: exact (file+line+rule) + cross-tool category
[3d] Per-Rule Cap             ← max 5 findings/rule (noise control)
[3e] Priority Sort            ← security/high first for within-limit AI coverage
    │
    ▼
[4]  AI Explanation           ← Cerebras LLM + RAG from config/rules.yml
    │
    ▼
[5]  Quality Gate             ← Configurable thresholds → exit 1 if failed
    │
    ▼
[6]  Output                   ← DB, PR comments, SARIF, Dashboard, Rich CLI
```

---

### Stage 0 — Rate Limit Check

**Component:** `CORE/utils/rate_limiter.py`

Redis-backed token bucket. Allows ≤1 analysis per repository per minute. If exceeded, the pipeline exits immediately with a `retry_after` message. Falls back gracefully if Redis is unavailable.

---

### Stage 1 — Database Run Creation

**Component:** `DATABASE/database.py` → `create_analysis_run()`

Creates a row in `analysis_runs` before any scanning starts. This gives every run a unique `run_id` for full traceability even if the scan fails partway through.

---

### Stage 2a — Detection Layer

**Component:** `TOOLS/run_checks.sh` (Python) · `CORE/adapters/js_adapter.py` (JS/TS) · `CORE/adapters/go_adapter.py` (Go)

#### Python Pipeline (7 tools)

| Tool | What it catches | Output |
|------|----------------|--------|
| Ruff | Style, unused imports, bad practices | JSON |
| Semgrep | Security patterns (custom + community rules) | JSON |
| Bandit | Python security issues | JSON |
| Vulture | Dead/unused code | Text |
| Radon | Cyclomatic complexity | JSON |
| jscpd | Copy-paste duplication | JSON |
| Secrets Detector | API keys, passwords, tokens | Internal |

#### JS/TS Pipeline (4 tools)

| Tool | What it catches | Output |
|------|----------------|--------|
| ESLint + eslint-plugin-security | 20+ JS security/style rules | JSON |
| Semgrep (21 custom rules) | OWASP JS patterns, NoSQL injection, SSRF, XSS | JSON |
| npm audit | CVE-matched dependency vulnerabilities | JSON |
| jscpd | Copy-paste duplication | JSON |

#### Go Pipeline (3 tools)

| Tool | What it catches | Output |
|------|----------------|--------|
| gosec | Go security vulnerabilities | JSON |
| staticcheck | Go static analysis and bug detection | Text |
| Semgrep (10 custom rules) | Go architecture security flaws, Goroutine leaks | JSON |

**Custom Semgrep JS rule sets** (`TOOLS/semgrep/js-*.yml`):
- `js-rules.yml` — Core security (eval injection, SQL/NoSQL, XSS, SSRF, path traversal)
- `js-taint-rules.yml` — Taint analysis architecture (SQL/cmd/eval sources→skins; Pro engine)
- `js-xxe.yml` — XXE via libxmljs
- `js-ejs-xss.yml` — EJS template XSS

**Custom Semgrep Go rules** (`TOOLS/semgrep/go-rules.yml`):
- `go-rules.yml` — Command injection, SQLi, hardcoded secrets, Goroutine leaks, defer-in-loop. Opt-in local-only execution.

**Output:** Raw JSON files saved to `DATA/outputs/`

---

### Stage 2b — Extra Scanners

**Component:** `CORE/engines/secrets_detector.py`, `CORE/engines/sca_scanner.py`

Run after the main tool sweep as a second detection pass:

- **Secrets Detector** — Finds hardcoded credentials, API keys, tokens. Uses regex + entropy analysis.
- **SCA Scanner** — Parses `requirements.txt` / `pyproject.toml` and checks against OSV/PyPI vulnerability database.

### CBoM Scanner (`CORE/engines/cbom_scanner.py`)

The Cryptographic Bill of Materials scanner inventories all cryptographic API usage in a codebase and classifies each algorithm by quantum-safety status, aligned with NIST's 2024 Post-Quantum Cryptography standardization (FIPS 203 ML-KEM, FIPS 204 ML-DSA).

**Classification tiers:**
- `CRYPTO-001` (HIGH): Non-quantum-safe algorithms — MD5, SHA1, RSA, ECDSA, DH, DSA, DES, RC4. Vulnerable to Shor's algorithm on quantum computers.
- `CRYPTO-002` (MEDIUM): Classically secure but not post-quantum-safe — SHA-256, SHA-512, AES-128, HMAC-SHA256, PBKDF2. Safe today, migration recommended.
- `CRYPTO-003` (LOW): Quantum-resistant — SHA3-256/384/512, BLAKE2b/s, AES-256, ChaCha20, bcrypt, Argon2, scrypt.

**Detection coverage:**
- Python: `hashlib`, `hmac`, `pycryptodome`, `cryptography` library, `bcrypt`, `argon2`, JWT libraries
- JavaScript/TypeScript: `node:crypto` (`createHash`, `createCipheriv`, `createSign`, `generateKeyPair`), WebCrypto `subtle` API, `bcrypt`, JWT

**Pipeline integration:**
The scanner runs inside `run_extra_scanners()` and emits canonical ACR-QA findings with a `cbom_metadata` field carrying algorithm name, quantum-safety status, category, and recommended replacement. A cross-tool deduplication group (`weak-hash-md5`) prevents double-reporting when Bandit (`SECURITY-009`) and CBoM (`CRYPTO-001`) both flag the same `hashlib.md5` call.

**Algorithm registry:** 28 entries covering hash, symmetric, asymmetric, KDF, MAC, and JWT algorithm families.

Both produce findings in the same canonical format and are merged into the main findings list before normalization.

---

### Stage 3a — Normalization

**Component:** `CORE/engines/normalizer.py`

Converts all tool-specific outputs into the canonical `Finding` schema. Maps 124+ tool-specific rule IDs to canonical rule IDs (e.g., `B301` → `SECURITY-008`, `F401` → `IMPORT-001`).

**Key features:**
- Inline suppression filtering (`# acr-qa:ignore`, `# acrqa:disable RULE-ID`)
- Pydantic v2 schema validation on every finding
- Raw tool output preserved in `tool_raw` field for provenance

---

### Stage 3b — Config Filtering

**Component:** `CORE/config_loader.py`

Loads `.acrqa.yml` from the project root and applies per-repo customizations:

| Config Key | Effect |
|-----------|--------|
| `disabled_rules` | Drop specific rule IDs |
| `enabled_rules` | Allowlist mode — drop everything else |
| `severity_overrides` | Reclassify a rule's severity |
| `ignore_paths` | Skip findings from matching file paths |
| `min_severity` | Drop `low` findings if threshold is `medium`, etc. |

---

### Stage 3c — Deduplication

**Component:** `CORE/main.py` → `_deduplicate_findings()`

Two-pass dedup:

1. **Exact:** Same `file + line + canonical_rule_id` → keep the finding from the higher-priority tool
2. **Cross-tool category:** Same `file + line + security category group` → e.g., Semgrep `CUSTOM-shell-injection` and Bandit `SECURITY-024` on the same line collapse to one finding

Tool priority: `Bandit/Semgrep/Secrets (3) > Vulture/Radon (2) > Ruff/jscpd (1)`

---

### Stage 3d — Per-Rule Cap

**Component:** `CORE/main.py` → `_cap_per_rule()`

Caps findings at **max 5 per canonical rule ID**. Prevents a single noisy rule (e.g., `STYLE-001`) from flooding the results and drowning out real security issues.

---

### Stage 3e — Priority Sort

**Component:** `CORE/main.py` → `_sort_by_priority()`

Sorts all findings before AI explanation:

```
High Security → Medium Security → High Design → ... → Low Style
```

This ensures that when an `max_explanations` cap is applied, the most important findings always get AI explanations first.

---

### Stage 4 — AI Explanation Engine (RAG)

**Component:** `CORE/engines/explainer.py`

For each finding (up to `max_explanations` from `.acrqa.yml`):

1. **Code extraction** — `code_extractor.py` pulls 3-line window around the finding
2. **Knowledge retrieval** — Looks up the canonical rule in `config/rules.yml` (66+ rules with rationale, CWE, remediation, examples)
3. **Prompt construction** — Evidence-grounded prompt: rule definition + code context + file path
4. **LLM call** — Cerebras Llama 3.1 8B (`llama3.1-8b`) via async Cerebras API
5. **Async pipeline** — All explanations fire simultaneously (23 findings → 1.12s wall time)
6. **Entropy scoring** — 3 calls at different temperatures, response consistency measured (0–1)
7. **Self-evaluation** — LLM rates its own output: relevance / accuracy / clarity (1–5 each)
8. **Redis caching** — Explanation cached by `finding_hash` to avoid duplicate LLM calls
9. **Fallback** — Template explanation used if API fails or confidence < threshold

---

### Stage 5 — Quality Gate

**Component:** `CORE/engines/quality_gate.py`

Evaluated **after** AI explanations so it gates on the final, processed finding set.

Configurable thresholds (from `.acrqa.yml`):

| Threshold | Default | Behavior |
|-----------|:-------:|---------|
| `mode` | `block` | `block` exits 1 to prevent merge; `warn` always exits 0 |
| `max_high` | 0 | Any high-severity finding fails the gate |
| `max_medium` | 10 | More than 10 medium findings fail |
| `max_total` | 100 | Total findings cap |
| `max_security` | 0 | Any security finding fails the gate |

Returns **exit code 1** when thresholds are exceeded and `mode: block` is set → blocks CI merge. In `warn` mode, threshold failures are reported but CI passes.

---

### Stage 6 — Output Layer

| Output | Component | Format |
|--------|-----------|--------|
| PostgreSQL | `DATABASE/database.py` | 5 tables |
| PR Comments | `scripts/post_pr_comments.py` + GitHub Actions | Inline PR comments via GitHub API |
| MR Comments | `scripts/post_gitlab_comments.py` | GitLab API |
| SARIF Export | `scripts/export_sarif.py` | SARIF v2.1.0 |
| Dashboard | `FRONTEND/app.py` | Flask + 20+ REST API endpoints |
| Rich CLI | `CORE/main.py --rich` | Terminal tables |
| Prometheus | `/metrics` endpoint | Prometheus text |

#### PR Bot — GitHub Actions Integration

`scripts/post_gate_comment.py` is wired to `.github/workflows/acrqa.yml`. On every PR:
1. Checkout target repo
2. Run `CORE/main.py --lang javascript --json` (or `--lang python`)
3. Findings persisted to PostgreSQL via `DATABASE/database.py`
4. Quality gate evaluated using `mode: block` or `warn`
5. `post_gate_comment.py` fetches the run results and posts an inline summary comment via GitHub REST API, automatically deleting old duplicates
5. Comment format: `🔴 [SECURITY-001] eval() at app.js:32 — Dynamic code execution...`

---

### Autofix PR Bot (`scripts/create_fix_pr.py`) — Feature 4

After every analysis run, ACR-QA can automatically open a GitHub PR containing only AI-generated fixes that passed linter validation.

**Fix validation chain:**
1. `ExplanationEngine` extracts the first code block from the AI response via regex
2. `validate_fix()` runs ruff (Python) or ESLint (JS) on the extracted code
3. If linting passes: `fix_validated=True`, `fix_code` stored in `llm_explanations` DB table
4. `create_fix_pr.py` calls `get_validated_fixes(run_id)` — only retrieves rows where `fix_validated=TRUE` and `fix_code IS NOT NULL`
5. Fixes are grouped by file, applied as line-level patches (reverse line order to preserve indices), and committed to a new branch via GitHub API
6. A PR is opened with a severity breakdown table and per-fix details including confidence level

**Key design decisions:**
- Uses GitHub API blobs — no local file manipulation required, works in any CI environment
- Only validated fixes are PRed — zero unverified AI suggestions reach the PR
- Previous autofix PRs for the same run are closed before creating a new one (no duplicate PRs)
- Gracefully exits with code 0 if no validated fixes exist

---

### Confidence Scorer (`CORE/engines/confidence_scorer.py`) — Feature 5

Every finding receives a 0-100 integer confidence score computed at insert time by `ConfidenceScorer`. Higher scores indicate higher likelihood of a true positive.

**Scoring signals (5 weighted components):**

| Signal | Max Points | Rationale |
|--------|-----------|-----------|
| Severity | 40 | High-severity findings are more likely actionable |
| Category | 20 | Security findings are higher confidence than style |
| Tool reliability | 15 | Bandit/Semgrep > Ruff > Vulture for security findings |
| Rule specificity | 10 | Known registry rules are better calibrated than unknown |
| Fix validated | 10 | If AI fix passed linting, finding is likely real |

**Score labels:** 90-100 = very high, 70-89 = high, 50-69 = medium, 30-49 = low, 0-29 = very low

**Pipeline integration:**
- `Database.insert_finding()` calls `ConfidenceScorer().score(finding)` before every DB insert
- Score stored in `findings.confidence_score` (INTEGER 0-100)
- Dashboard slider filters findings by minimum confidence threshold
- `GET /api/runs/<id>/findings?min_confidence=70` returns only high-confidence findings

---

### Triage Memory (`CORE/engines/triage_memory.py`) — Feature 6

The triage memory system learns from user feedback to automatically suppress recurring false positives in future scans.

**How it works:**
1. User marks a finding as FP via the dashboard or `POST /api/findings/<id>/false-positive`
2. `learn_from_fp(finding_id, db)` extracts the finding's `canonical_rule_id` and derives a file glob pattern (e.g. `tests/test_auth.py` → `tests/test_*.py`)
3. A suppression rule is inserted into the `suppression_rules` table
4. On every subsequent scan, `suppress_findings()` runs after config filters and removes findings that match any active rule
5. `suppression_count` is incremented each time a rule suppresses a finding — tracks effectiveness

**Pattern derivation:** Test files (`test_*.py`, `*.spec.js`) are grouped by directory. Non-test files suppress on exact file path. This prevents overly broad suppression while still catching recurring FPs in test suites.

**Pipeline integration:** Both `AnalysisPipeline.run()` (Python) and `AnalysisPipeline.run_js()` (JS/TS) call `suppress_findings()` after `_apply_config_filters()`.

**API:** `GET /api/suppression-rules` returns all active rules with their suppression counts for dashboard visibility.

---

### Path Feasibility Validator (`CORE/engines/path_feasibility.py`) — Feature 7

For HIGH and CRITICAL security findings, a second AI call validates whether the flagged execution path is actually reachable at runtime. This reduces false positives by eliminating unreachable code paths before they reach the developer.

**Academic basis:** Implements the core approach from LLM4PFA (arXiv) — using LLMs to validate path feasibility in static analysis pipelines.

**Verdict system:**
- `REACHABLE` — path is reachable, finding is likely a true positive (no penalty)
- `UNREACHABLE` — path cannot be reached, likely a false positive (confidence penalty: HIGH=-30, MEDIUM=-20, LOW=-10)
- `UNKNOWN` — insufficient context (small penalty: -5)

**Eligibility:** Only HIGH/CRITICAL severity findings in the `security` category are validated. Medium/low findings and non-security categories are skipped to keep latency and cost manageable.

**Pipeline integration:**
- Runs inside `_explain_one_async()` after fix validation, using the same `httpx.AsyncClient` session
- No sequential latency — feasibility check runs in the existing async context
- Results stored in `llm_explanations`: `feasibility_verdict`, `feasibility_confidence`, `feasibility_reasoning`, `feasibility_latency_ms`, `feasibility_penalty`
- Temperature set to 0.1 for deterministic verdicts (vs 0.3 for explanations)

### Dependency Reachability (`CORE/engines/dependency_reachability.py`) — Feature 8

For npm audit findings, ACR-QA checks whether the vulnerable package is actually imported in the application's source code or only present as a transitive dependency.

**Reachability levels:**
- `DIRECT` — package is explicitly `require()`d or `import`ed → confidence unchanged, full risk
- `TRANSITIVE` — package installed but never directly imported → confidence -15 (harder to exploit)
- `UNKNOWN` — not found in package.json or source → confidence -5 (likely transitive noise)

**How it works:**
1. Parses `package.json` to get declared dependencies
2. Scans all `.js/.ts/.jsx/.tsx/.mjs/.cjs` files (excluding `node_modules`, `dist`, `build`)
3. Extracts `require('pkg')` and `import ... from 'pkg'` using regex
4. Normalises scoped packages and subpath imports (`@org/pkg/utils` → `@org/pkg`)
5. `enrich_findings()` adds `reachability_level`, `reachability_penalty`, `reachability_direct_imports` to each npm finding and adjusts `confidence_score`

**Verified on NodeGoat:** `ansi-regex` CVE flagged by npm audit — correctly classified as `UNKNOWN` since NodeGoat never directly imports it (it enters via a transitive dependency chain).

---

### Cross-Language Correlator (`CORE/engines/cross_language_correlator.py`) — Feature 9

Detects vulnerability chains that span Python backend code, Jinja2/HTML templates, and JavaScript frontend files in the same project. Inspired by CHARON (CISPA/NDSS).

**Correlation types:**

| Type | Trigger | Confidence Boost |
|------|---------|------------------|
| `SQLI_TO_TEMPLATE` | SQL injection in DAO + route renders result in template | +20 |
| `TEMPLATE_INJECTION` | `autoescape=False` or `\|safe` filter + backend security findings | +15 |
| `XSS_CHAIN` | Python XSS finding + template unsafe output | +15 |
| `ROUTE_JS_CHAIN` | Python security finding + JS file in same feature directory | +10 |

**Pipeline integration:** Runs in both `run()` and `run_js()` before the quality gate assignment. Calls `enrich_findings()` which tags correlated findings with `cross_language_correlation`, `correlation_chain`, and `correlation_severity` fields, and boosts `confidence_score` for findings that are part of a chain.

**Verified on DVPWA:** 2 chains detected — SQL injection in `dao/student.py` chained to 7 Jinja2 templates, and `autoescape=False` in `app.py` flagged as global XSS risk across all templates.

---

## Database Schema

6 tables in PostgreSQL 15:

| Table | Purpose |
|-------|---------|
| `analysis_runs` | Run metadata (repo, PR, status, timestamps) |
| `findings` | Detected issues with canonical schema + raw output |
| `llm_explanations` | AI explanations with full provenance (prompt, response, latency, model) |
| `pr_comments` | Posted PR/MR comments |
| `feedback` | User false-positive / helpfulness feedback |
| `suppression_rules` | Learned FP suppression rules (Feature 6 — Triage Memory) |

---

## Security Architecture

- **Non-root Docker** — Container runs as `acrqa` user
- **Health checks** — Docker HEALTHCHECK on `/api/health`
- **Secrets** — Environment variables only, never logged
- **SQL injection** — Parameterized queries throughout
- **Rate limiting** — Redis-backed token bucket (1 req/repo/min)
- **Input validation** — Pydantic v2 schema validation on all findings
- **Inline suppression audit** — Suppressed findings logged, not silently dropped

---

## Scalability

- **Parallel detection** — All tools run concurrently in `run_checks.sh`
- **Async AI** — All LLM explanation calls fired simultaneously (23 explanations → 1.12s wall time)
- **Configurable limits** — `max_explanations` caps AI calls per run
- **Redis caching** — Explanation cache avoids duplicate LLM calls across runs
- **Graceful degradation** — Fully functional without Redis (in-memory fallback)
- **Diff-only mode** — `--diff-only` flag scans only PR-changed files for faster CI

### Scale Benchmark Results (v3.0.3)

| Synthetic Target | Files | Execution Time | Throughput |
|------------------|:-----:|:--------------:|:----------:|
| Baseline | 10 | 6.31s | 1.6 files/s |
| Mid | 50 | 6.50s | 7.7 files/s |
| High | 100 | 7.11s | 14.1 files/s |
| Large | 200 | 7.58s | 26.4 files/s |
| Massive | 500 | 9.83s | 50.9 files/s |

> 50× files → 1.6× time. Overhead dominates at small scale; throughput scales efficiently at large scale.

### Vulnerability Trend Dashboard — Feature 10

Time-series visualization of finding counts, severity distribution, and confidence scores across all historical ACR-QA scans stored in PostgreSQL.

**API endpoints:**
- `GET /api/trends?limit=30&repo=dvna` — returns time-series data for Chart.js rendering. Supports optional repo filter. Returns: `labels`, `severity_series` (high/medium/low), `category_series` (security/style/design/best_practice), `confidence_series` (avg per run), `total_series`, `repos` list.
- `GET /api/repos` — returns distinct repo names with completed runs (excludes test- repos)

**Dashboard charts (Chart.js 4.x):**
- Severity trend — stacked line chart of HIGH/MEDIUM/LOW counts over time
- Confidence trend — line chart of average confidence score per run
- Category breakdown — doughnut chart of finding categories

**Bug fixed:** `/api/trends` was reading `row.get("created_at")` but the DB returns `started_at` — labels were all "unknown". Fixed to `row.get("started_at")`.
