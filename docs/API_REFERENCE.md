# ACR-QA REST API Reference

**Base URL:** `http://localhost:8000`
**Version:** v4.0.0 (Phase 12)
**Format:** All responses are `application/json`
**Auth:** All `/v1/` endpoints require `Authorization: Bearer <token>` or `X-API-Key: <key>`

> ⚠️ Flask is fully removed (v3.6.1). The only server is FastAPI at `:8000`. Swagger UI is at `/docs`.
> This document covers the 32 async endpoints under `/v1/` in `FRONTEND/api/routers/`.

**Get a token:**
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@acrqa.local","password":"changeme123!"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

---

## Authentication

No authentication required for local deployment. For production (Railway), set `FLASK_SECRET_KEY` in `.env`.

---

## Endpoints

### Dashboard

#### `GET /`
Returns the HTML dashboard. Not for API use — browser only.

---

### Runs

#### `GET /api/runs`
List all analysis runs.

**Response:**
```json
[
  {
    "id": 1,
    "repo_name": "my-project",
    "run_at": "2026-04-05T10:00:00",
    "total_findings": 42,
    "high_count": 2,
    "medium_count": 8,
    "low_count": 32,
    "gate_passed": false
  }
]
```

#### `GET /api/runs/<run_id>/findings`
Get all findings for a specific run.

**Query params:**
- `severity` — filter by `high`, `medium`, `low`
- `category` — filter by category name
- `page` — pagination (default: 1)
- `per_page` — results per page (default: 50)

**Response:**
```json
{
  "findings": [...],
  "total": 42,
  "page": 1,
  "per_page": 50
}
```

#### `GET /api/runs/<run_id>/stats`
Summary statistics for a run.

**Response:**
```json
{
  "total": 42,
  "high": 2,
  "medium": 8,
  "low": 32,
  "by_category": {"security": 5, "style": 20, ...},
  "gate_passed": false,
  "gate_details": {...}
}
```

#### `GET /api/runs/<run_id>/summary`
PR-comment-ready summary (markdown formatted).

#### `GET /api/runs/<run_id>/compliance`
OWASP Top 10 compliance report for the run.

**Response:**
```json
{
  "owasp_coverage": {"A01": {...}, "A03": {...}},
  "covered_categories": 7,
  "total_categories": 10
}
```

#### `GET /api/runs/<run_id>/cost-benefit`
Analysis of remediation ROI — findings by cost-to-fix vs risk.

---

### Analysis

#### `POST /api/analyze`
Run ACR-QA on a target directory (async pipeline trigger).

**Body:**
```json
{
  "target_dir": "/path/to/project",
  "repo_name": "my-project",
  "pr_number": 42,
  "limit": 10,
  "no_ai": false
}
```

**Response:**
```json
{"run_id": 7, "status": "completed", "findings_count": 42}
```

#### `POST /api/refresh-findings`
Re-run analysis using cached tool outputs (skips tool execution, re-normalizes only).

#### `GET /api/quick-stats`
Latest run stats without full findings list. Lightweight polling endpoint.

---

### Findings

#### `POST /api/findings/<finding_id>/feedback`
Submit 👍/👎 feedback on a finding.

**Body:**
```json
{"rating": "positive", "comment": "This is a real issue"}
```

#### `POST /api/findings/<finding_id>/mark-false-positive`
Mark a finding as a confirmed false positive. Updates severity_overrides.yml.

**Body:**
```json
{"reason": "MD5 used for cache key, not security"}
```

---

### Quality & Config

#### `GET /api/categories`
List all canonical rule categories.

#### `GET /api/health`
Health check — returns database + Redis connectivity status.

**Response:**
```json
{"status": "ok", "db": "connected", "redis": "connected", "version": "3.1.3"}
```

#### `GET /api/fix-confidence/<rule_id>`
Auto-fix confidence score for a given canonical rule ID.

**Response:**
```json
{"rule_id": "SECURITY-001", "can_fix": true, "confidence": 92}
```

#### `GET /api/policy`
Current `.acrqa.yml` policy loaded for this session.

#### `GET /api/trends`
Finding counts over time (last 10 runs) for trend visualization.

---

### Specialized Scans

#### `POST /api/scan/secrets`
Scan for hardcoded secrets/API keys.

**Body:** `{"target_dir": "/path/to/project"}`

#### `POST /api/scan/sca`
Software Composition Analysis — scan dependencies for known CVEs.

**Body:** `{"target_dir": "/path/to/project"}`

#### `POST /api/scan/ai-detection`
Detect AI-generated code patterns (heuristic + metric-based).

**Body:** `{"target_dir": "/path/to/project"}`

---

### Test Gaps

#### `GET /api/test-gaps`
AST-based test gap analysis — finds public functions with no corresponding test.

**Response:**
```json
{
  "untested_functions": [
    {"function": "process_payment", "file": "payments.py", "line": 42}
  ],
  "coverage_estimate": "73%"
}
```

---

## CLI Reference

```bash
# Basic usage
python -m CORE --target-dir ./myproject

# Skip AI explanations (fast mode — good for CI)
python -m CORE --target-dir ./myproject --no-ai

# JSON output to stdout (for JS consumers)
python -m CORE --target-dir ./myproject --no-ai --json > results.json

# Beautiful terminal output
python -m CORE --target-dir ./myproject --rich

# Only analyze changed files (PR diff mode)
python -m CORE --target-dir ./myproject --diff-only --diff-base main

# Generate auto-fix suggestions
python -m CORE --target-dir ./myproject --auto-fix

# Check version
python -m CORE --version
```

### Exit Codes
| Code | Meaning |
|------|---------|
| `0` | Quality gate passed (or not checked) |
| `1` | Quality gate failed — use in CI to block merges |

---

## Error Responses

All endpoints return standard error shape:
```json
{"error": "Description of what went wrong", "status": 404}
```

---

## JS Integration Example

```javascript
// Trigger an analysis
const response = await fetch('http://localhost:5000/api/analyze', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({target_dir: './src', repo_name: 'my-app', no_ai: true})
});
const {run_id} = await response.json();

// Poll for findings
const findings = await fetch(`http://localhost:5000/api/runs/${run_id}/findings`);
const data = await findings.json();
console.log(`Found ${data.total} issues`);
```

---

## New Endpoints (v3.6.0 – v3.8.0)

### `GET /v1/runs/{run_id}/attestation` [v3.6.0]

Returns the SLSA-grade provenance attestation for a completed scan run.

**Response:**
```json
{
  "run_id": 42,
  "key_id": "sha256:abc123",
  "created_at": "2026-05-15T10:00:00",
  "signature_algorithms": ["ECDSA-P256", "Dilithium3"],
  "post_quantum": true,
  "signature_valid": true,
  "bundle": { "attestation": {...}, "signatures": [...] }
}
```

---

### `GET /v1/runs/{run_id}/findings/{finding_id}/autofix` [v3.7.0]

Generate an LLM-powered unified-diff patch for a specific finding. Falls back to rule-based fix if LLM unavailable.

**Response:**
```json
{
  "finding_id": 7,
  "run_id": 42,
  "rule_id": "SECURITY-027",
  "patch": "--- original\n+++ fixed\n...",
  "confidence": 0.85,
  "explanation": "Replaced f-string SQL query with parameterized ?",
  "valid": true,
  "validation_note": "re_scan_passed"
}
```

---

### `GET /v1/runs/{run_id}/sbom` [v3.8.0]

Return the CycloneDX 1.4 Software Bill of Materials for a run. Returns stored SBOM if available; generates on-the-fly from `dependency_findings` otherwise.

**Response:**
```json
{
  "success": true,
  "run_id": 42,
  "sbom": {
    "bomFormat": "CycloneDX",
    "specVersion": "1.4",
    "serialNumber": "urn:uuid:...",
    "metadata": { "timestamp": "...", "component": {...}, "tools": [...] },
    "components": [{"type":"library","name":"requests","version":"2.28.0","purl":"pkg:pypi/requests@2.28.0"}],
    "vulnerabilities": [...]
  }
}
```

---

### `GET /v1/runs/{run_id}/supply-chain` [v3.8.0]

Return dependency findings with CVE data and risk scores.

**Query params:** `?risk_level=high|medium|low` (optional filter)

**Response:**
```json
{
  "success": true,
  "run_id": 42,
  "summary": {
    "total": 45,
    "high_risk": 3,
    "medium_risk": 12,
    "low_risk": 30,
    "total_cves": 7
  },
  "dependencies": [
    {
      "name": "requests",
      "version": "2.28.0",
      "ecosystem": "PyPI",
      "risk_score": 45,
      "risk_level": "medium",
      "cve_count": 1,
      "cve_ids": ["CVE-2023-32681"],
      "stars": 51000,
      "last_commit_days": 14,
      "contributors": 780,
      "archived": false
    }
  ]
}
```

---

## Findings Response Fields (v3.6.3+)

The `GET /v1/runs/{id}/findings` response now includes taint and triage fields:

| Field | Type | Source | Since |
|---|---|---|---|
| `taint_source` | string\|null | TaintAnalyzer | v3.6.3 |
| `taint_path` | string\|null | TaintAnalyzer | v3.6.3 |
| `taint_confidence` | float\|null | TaintAnalyzer | v3.6.3 |
| `triage_verdict` | `true_positive`\|`false_positive`\|`needs_review`\|null | TriageAgent | v3.6.5 |
| `triage_reasoning` | string\|null | TriageAgent | v3.6.5 |
| `triage_confidence_delta` | float\|null | TriageAgent (±applied to confidence) | v3.6.5 |

---

---

## New Endpoints (Phase 12 Week 5 — v4.0.0)

### `GET /v1/runs/{run_id}/cost` [Phase 12 W5 — Task 12.32]

Per-run Groq token cost telemetry (FinOps). Written after each analysis run completes via `Database.update_run_cost()`.

**Response:**
```json
{
  "success": true,
  "run_id": 42,
  "groq_tokens_used": 18450,
  "groq_cost_usd": 0.004982,
  "groq_requests": 12
}
```

**Fields:**
| Field | Type | Description |
|---|---|---|
| `groq_tokens_used` | integer\|null | Total Groq tokens consumed across all explanations |
| `groq_cost_usd` | float | Estimated USD cost at $0.27/1M tokens (llama3-8b-8192) |
| `groq_requests` | integer\|null | Number of Groq API calls (excludes cache hits and fallbacks) |

**Notes:**
- Returns `null` fields for runs completed before migration 0010 (pre-Phase 12 Week 5)
- Aggregate cost across all runs available at `GET /v1/cost-summary`

---

*Last updated: May 15, 2026 — ACR-QA v4.0.0 (Phase 12 Week 5)*
