# ACR-QA v2.5 Architecture

## System Overview

ACR-QA is a modular, pipeline-based system for automated code review with RAG-enhanced AI explanations. It runs 7 static analysis tools, normalizes all findings into a canonical schema, generates evidence-grounded explanations, and enforces configurable quality gates.

## Pipeline Stages

```
Source Code → Detection → Normalization → Config Filtering → Dedup → Scoring → AI Explanation → Quality Gate → Output
```

### 1. Detection Layer

Runs 7 tools in parallel via `TOOLS/run_checks.sh`:

| Tool | Engine | Output Format |
|------|--------|---------------|
| Ruff | `ruff check --output-format json` | JSON |
| Semgrep | `semgrep --config TOOLS/semgrep/` | JSON |
| Bandit | `bandit -r -f json` | JSON |
| Vulture | `vulture` | Text (parsed) |
| Radon | `radon cc -j` | JSON |
| Secrets Detector | `CORE/engines/secrets_detector.py` | Custom |
| SCA Scanner | `CORE/engines/sca_scanner.py` | Custom |

**Output:** Raw JSON files in `DATA/outputs/`

### 2. Normalization Layer

**Component:** `CORE/engines/normalizer.py`

Converts tool-specific outputs into the canonical schema. Maps 71 tool-specific rules to 47 canonical rule IDs (e.g., `B301` → `SECURITY-008`, `F401` → `IMPORT-001`).

**Key features:**
- Inline suppression filtering (`# acr-qa:ignore`, `# acrqa:disable RULE-ID`)
- Pydantic v2 schema validation on every finding
- Raw tool output preserved in `tool_raw` field for provenance

### 3. Config Filtering

**Component:** `CORE/config_loader.py`

Loads `.acrqa.yml` and applies:
- Rule enable/disable (`disabled_rules`, `enabled_rules`)
- Severity overrides (`severity_overrides`)
- Path ignoring (`ignore_paths`)
- Minimum severity threshold (`min_severity`)

### 4. Deduplication

**Component:** `CORE/main.py` → `_deduplicate_findings()`

Cross-tool dedup by `file + line + rule_id` with tool priority:
1. Security tools (Bandit, Semgrep) — highest priority
2. Specialized tools (Vulture, Radon)
3. General tools (Ruff) — lowest priority

### 5. Severity Scoring

**Component:** `CORE/engines/severity_scorer.py`

Context-aware severity assignment considering:
- Tool-reported severity
- Rule category (security findings auto-elevated)
- Code complexity metrics
- Finding density per file

### 6. AI Explanation Engine (RAG)

**Component:** `CORE/engines/explainer.py`

1. **Context extraction** — `CORE/utils/code_extractor.py` extracts 3-line window around finding
2. **Knowledge retrieval** — Looks up rule in `config/rules.yml` (66 rules with rationale, remediation, examples)
3. **Prompt construction** — Evidence-grounded prompt with rule definition + code context
4. **LLM call** — Cerebras Llama 3.1 8B (free tier)
5. **Entropy scoring** — Runs LLM 3× with different temperatures, measures response consistency (0–1)
6. **Self-evaluation** — LLM rates its own output on relevance / accuracy / clarity (1–5)
7. **Fallback** — Template explanation if API fails or confidence too low

### 7. Quality Gate

**Component:** `CORE/engines/quality_gate.py`

Configurable thresholds (from `.acrqa.yml`):
- `max_high`: Maximum high-severity findings (default: 0)
- `max_medium`: Maximum medium-severity findings (default: 10)
- `max_total`: Maximum total findings (default: 100)
- `max_security`: Maximum security findings (default: 0)

**Returns exit code 1** when thresholds exceeded → blocks CI merge.

### 8. Output Layer

| Output | Component | Format |
|--------|-----------|--------|
| PostgreSQL | `DATABASE/database.py` | 5 tables |
| PR Comments | `scripts/post_pr_comments.py` | GitHub API |
| MR Comments | `scripts/post_gitlab_comments.py` | GitLab API |
| SARIF Export | `scripts/export_sarif.py` | SARIF v2.1.0 |
| Dashboard | `FRONTEND/app.py` | Flask + REST API |
| Rich CLI | `CORE/main.py --rich` | Terminal tables |
| Prometheus | `/metrics` endpoint | Prometheus text |

## Database Schema

5 tables in PostgreSQL 15:

| Table | Purpose |
|-------|---------|
| `analysis_runs` | Run metadata (repo, PR, status, timestamps) |
| `findings` | Detected issues with canonical schema + raw output |
| `llm_explanations` | AI explanations with full provenance (prompt, response, latency, model) |
| `pr_comments` | Posted PR/MR comments |
| `feedback` | User false-positive / helpfulness feedback |

## Security Architecture

- **Non-root Docker** — Container runs as `acrqa` user
- **Health checks** — Docker HEALTHCHECK on `/api/health`
- **Secrets** — Environment variables only, never logged
- **SQL injection** — Parameterized queries throughout
- **Rate limiting** — Redis-backed token bucket (1 req/repo/min)
- **Input validation** — Pydantic v2 schema validation on all findings
- **Inline suppression audit** — Suppressed findings logged, not silently dropped

## Scalability

- **Parallel detection** — All 7 tools run concurrently
- **Configurable limits** — `max_explanations` caps AI calls per run
- **Redis caching** — Explanation cache to avoid duplicate LLM calls
- **Graceful degradation** — Works without Redis (falls back to in-memory)
- **Batch processing** — Findings processed in configurable batches