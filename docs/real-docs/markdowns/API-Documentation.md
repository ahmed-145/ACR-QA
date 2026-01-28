# ACR-QA API Documentation

**Version:** 2.0  
**Base URL:** `http://localhost:5000`  
**Last Updated:** January 28, 2026

---

## Table of Contents
1. [Authentication](#authentication)
2. [Endpoints](#endpoints)
3. [Data Models](#data-models)
4. [Error Handling](#error-handling)
5. [Examples](#examples)

---

## Authentication

**Current:** No authentication required (development mode)  
**Future:** Bearer token authentication

```bash
# Future usage
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:5000/api/runs
```

---

## Endpoints

### 1. Get Recent Analysis Runs

**GET** `/api/runs`

Retrieve a list of recent code analysis runs.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 10 | Maximum number of runs to return |

**Response:**
```json
{
  "success": true,
  "runs": [
    {
      "id": 42,
      "repo_name": "my-repo",
      "pr_number": 123,
      "status": "complete",
      "started_at": "2026-01-28T15:30:00",
      "total_findings": 15,
      "high_count": 2,
      "medium_count": 5,
      "low_count": 8
    }
  ]
}
```

**Example:**
```bash
curl http://localhost:5000/api/runs?limit=5
```

---

### 2. Get Findings for a Run

**GET** `/api/runs/{run_id}/findings`

Retrieve all findings for a specific analysis run with optional filters.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `run_id` | integer | Analysis run ID |

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `severity` | string | Filter by severity: `high`, `medium`, `low` |
| `category` | string | Filter by category: `security`, `design`, `style`, etc. |
| `search` | string | Search in file path, message, or rule ID |
| `group_by` | string | Group results: `rule` for grouping by rule ID |

**Response (Normal):**
```json
{
  "success": true,
  "run_id": 42,
  "total": 15,
  "findings": [
    {
      "id": 123,
      "canonical_rule_id": "SECURITY-001",
      "category": "security",
      "canonical_severity": "high",
      "file_path": "app/auth.py",
      "line": 42,
      "message": "SQL injection vulnerability detected",
      "explanation_text": "This code is vulnerable to SQL injection...",
      "confidence": 0.9,
      "cites_rule": true
    }
  ]
}
```

**Response (Grouped by Rule):**
```json
{
  "success": true,
  "grouped": true,
  "run_id": 42,
  "groups": [
    {
      "rule_id": "SECURITY-001",
      "count": 3,
      "severity": "high",
      "category": "security",
      "findings": [...]
    }
  ]
}
```

**Examples:**
```bash
# Get all findings
curl http://localhost:5000/api/runs/42/findings

# Filter by severity
curl http://localhost:5000/api/runs/42/findings?severity=high

# Search for specific file
curl http://localhost:5000/api/runs/42/findings?search=auth.py

# Group by rule
curl http://localhost:5000/api/runs/42/findings?group_by=rule
```

---

### 3. Mark Finding as False Positive

**POST** `/api/findings/{finding_id}/mark-false-positive`

Mark a finding as a false positive to improve future analysis.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `finding_id` | integer | Finding ID |

**Request Body:**
```json
{
  "reason": "This is expected behavior in our codebase"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Finding marked as false positive"
}
```

**Example:**
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"reason": "Expected behavior"}' \
  http://localhost:5000/api/findings/123/mark-false-positive
```

---

### 4. Get Run Summary

**GET** `/api/runs/{run_id}/summary`

Get statistical summary of an analysis run.

**Response:**
```json
{
  "success": true,
  "summary": {
    "run_id": 42,
    "findings_count": 15,
    "high_severity_count": 2,
    "medium_severity_count": 5,
    "low_severity_count": 8,
    "categories": {
      "security": 3,
      "design": 5,
      "style": 7
    }
  }
}
```

---

## Data Models

### Finding Object

```typescript
{
  id: number;                    // Unique finding ID
  canonical_rule_id: string;     // Rule identifier (e.g., "SECURITY-001")
  category: string;              // Category: security, design, style, etc.
  canonical_severity: string;    // Severity: high, medium, low
  file_path: string;             // Relative file path
  line: number;                  // Line number
  column?: number;               // Column number (optional)
  message: string;               // Issue description
  explanation_text?: string;     // AI-generated explanation
  confidence?: number;           // Confidence score (0.0-1.0)
  cites_rule?: boolean;          // Whether explanation cites rule
  is_false_positive?: boolean;   // Marked as false positive
}
```

### Run Object

```typescript
{
  id: number;                    // Unique run ID
  repo_name: string;             // Repository name
  pr_number?: number;            // Pull request number (optional)
  status: string;                // Status: pending, complete, failed
  started_at: string;            // ISO 8601 timestamp
  completed_at?: string;         // ISO 8601 timestamp (optional)
  total_findings: number;        // Total findings count
  high_count: number;            // High severity count
  medium_count: number;          // Medium severity count
  low_count: number;             // Low severity count
}
```

---

## Error Handling

### Error Response Format

```json
{
  "success": false,
  "error": "Error message description",
  "code": "ERROR_CODE"
}
```

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 400 | Bad Request | Invalid parameters |
| 404 | Not Found | Resource not found |
| 500 | Internal Server Error | Server error |

### Common Errors

**Run Not Found:**
```json
{
  "success": false,
  "error": "Run not found",
  "code": "RUN_NOT_FOUND"
}
```

**Invalid Severity:**
```json
{
  "success": false,
  "error": "Invalid severity. Must be: high, medium, or low",
  "code": "INVALID_SEVERITY"
}
```

---

## Examples

### Complete Workflow

```bash
# 1. Get recent runs
curl http://localhost:5000/api/runs

# 2. Get findings for run #42
curl http://localhost:5000/api/runs/42/findings

# 3. Filter high severity issues
curl http://localhost:5000/api/runs/42/findings?severity=high

# 4. Mark finding as false positive
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"reason": "Expected behavior"}' \
  http://localhost:5000/api/findings/123/mark-false-positive

# 5. Get summary
curl http://localhost:5000/api/runs/42/summary
```

### Python Example

```python
import requests

BASE_URL = "http://localhost:5000"

# Get recent runs
response = requests.get(f"{BASE_URL}/api/runs", params={"limit": 5})
runs = response.json()["runs"]

# Get findings for first run
run_id = runs[0]["id"]
response = requests.get(f"{BASE_URL}/api/runs/{run_id}/findings")
findings = response.json()["findings"]

# Filter high severity
response = requests.get(
    f"{BASE_URL}/api/runs/{run_id}/findings",
    params={"severity": "high"}
)
high_severity = response.json()["findings"]

# Mark false positive
finding_id = findings[0]["id"]
requests.post(
    f"{BASE_URL}/api/findings/{finding_id}/mark-false-positive",
    json={"reason": "Expected behavior"}
)
```

### JavaScript Example

```javascript
const BASE_URL = 'http://localhost:5000';

// Get recent runs
const runs = await fetch(`${BASE_URL}/api/runs?limit=5`)
  .then(r => r.json())
  .then(data => data.runs);

// Get findings
const runId = runs[0].id;
const findings = await fetch(`${BASE_URL}/api/runs/${runId}/findings`)
  .then(r => r.json())
  .then(data => data.findings);

// Mark false positive
await fetch(`${BASE_URL}/api/findings/123/mark-false-positive`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ reason: 'Expected behavior' })
});
```

---

## Rate Limiting

**Current:** No rate limiting on API endpoints  
**Analysis Rate Limit:** 1 analysis per repository per minute (enforced in pipeline)

---

## CORS

CORS is enabled for all origins in development mode.

**Production:** Configure allowed origins in environment variables.

---

## Changelog

### v2.0 (January 2026)
- Initial API release
- Added filtering and grouping
- Added false positive marking

---

**Need Help?**  
- GitHub: [ACR-QA Repository](https://github.com/ahmed-145/ACR-QA)
- Issues: [Report a Bug](https://github.com/ahmed-145/ACR-QA/issues)
