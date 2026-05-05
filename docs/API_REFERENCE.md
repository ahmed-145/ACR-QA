# ACR-QA REST API Reference

**Base URL:** `http://localhost:5000`
**Version:** v3.2.5
**Format:** All responses are `application/json`

> This document covers all 22 REST endpoints exposed by `FRONTEND/app.py`.
> These endpoints are stable and ready for consumption by JS frontends, VS Code extensions, or CI integrations.

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

*Last updated: May 5, 2026 — ACR-QA v3.2.5*
