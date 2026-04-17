# ACR-QA v3.0.3 Architecture

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

**Component:** `TOOLS/run_checks.sh` (Python) · `CORE/adapters/js_adapter.py` (JS/TS)

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

**Custom Semgrep JS rule sets** (`TOOLS/semgrep/js-*.yml`):
- `js-rules.yml` — Core security (eval injection, SQL/NoSQL, XSS, SSRF, path traversal)
- `js-taint-rules.yml` — Taint analysis architecture (SQL/cmd/eval sources→skins; Pro engine)
- `js-xxe.yml` — XXE via libxmljs
- `js-ejs-xss.yml` — EJS template XSS

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

## Database Schema

5 tables in PostgreSQL 15:

| Table | Purpose |
|-------|---------|
| `analysis_runs` | Run metadata (repo, PR, status, timestamps) |
| `findings` | Detected issues with canonical schema + raw output |
| `llm_explanations` | AI explanations with full provenance (prompt, response, latency, model) |
| `pr_comments` | Posted PR/MR comments |
| `feedback` | User false-positive / helpfulness feedback |

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
