# ACR-QA Canonical Finding Schema

All findings from all 7 tools are normalized to this universal format before storage and explanation.

## Schema Definition

```json
{
  "finding_id": "uuid-v4",
  "canonical_rule_id": "SECURITY-001",
  "original_rule_id": "B307",
  "tool": "bandit",
  "file": "path/to/file.py",
  "line": 42,
  "column": 5,
  "end_line": 42,
  "severity": "high",
  "canonical_severity": "high",
  "category": "security",
  "message": "Use of eval() detected",
  "description": "eval() can execute arbitrary code and should be avoided",
  "confidence": 0.92,
  "evidence": {
    "snippet": "result = eval(user_input)",
    "context_before": ["# Process user command", "def execute(user_input):"],
    "context_after": ["    return result", ""]
  },
  "tool_raw": {
    "tool_name": "bandit",
    "original_severity": "HIGH",
    "original_confidence": "HIGH",
    "original_output": { }
  }
}
```

## Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `finding_id` | string | Yes | UUID v4 identifier |
| `canonical_rule_id` | string | Yes | ACR-QA rule ID (e.g., `SECURITY-001`, `IMPORT-001`) |
| `original_rule_id` | string | Yes | Tool-native rule ID (e.g., `B307`, `F401`) |
| `tool` | string | Yes | Source tool: `ruff`, `bandit`, `semgrep`, `vulture`, `radon`, `secrets`, `sca` |
| `file` | string | Yes | Relative file path |
| `line` | integer | Yes | Line number (1-indexed) |
| `column` | integer | No | Column number |
| `end_line` | integer | No | End line for multi-line findings |
| `severity` | string | Yes | Original tool severity |
| `canonical_severity` | string | Yes | Normalized: `high`, `medium`, `low` |
| `category` | string | Yes | Finding category (see below) |
| `message` | string | Yes | Human-readable issue description |
| `description` | string | No | Extended description |
| `confidence` | float | No | Confidence score (0.0–1.0) |
| `evidence` | object | No | Code context around the finding |
| `tool_raw` | object | Yes | Original tool output (preserved for provenance) |

## Categories

| Category | Description | Example Rules |
|----------|-------------|---------------|
| `security` | Security vulnerabilities | `SECURITY-001` (eval), `SECURITY-027` (SQL injection) |
| `design` | Design and architecture issues | `SOLID-001` (too many params), `COMPLEX-001` |
| `style` | Code style and formatting | `IMPORT-001`, `VAR-001`, `NAMING-001` |
| `dead-code` | Unreachable or unused code | `DEAD-001`, `DEAD-002` |
| `performance` | Performance concerns | `PERF-001`, `PERF-002` |
| `best-practice` | Best practice violations | `EXCEPT-001`, `RETURN-001` |
| `duplication` | Code duplication | `DUP-001` |
| `documentation` | Missing or incorrect docs | `DOC-001`, `DOC-002` |
| `concurrency` | Threading/async issues | `ASYNC-001` |

## Severity Mapping

| Canonical | Meaning | CI Impact |
|-----------|---------|-----------|
| `high` | Critical issue, must fix | Blocks merge (if quality gate enabled) |
| `medium` | Should fix, may indicate problems | Configurable threshold |
| `low` | Informational, nice to fix | Reported but doesn't block |

## Validation

All findings are validated against a Pydantic v2 model before storage. Invalid findings are logged and dropped.

```python
from pydantic import BaseModel

class CanonicalFinding(BaseModel):
    tool: str
    rule_id: str
    file: str
    line: int
    severity: str
    category: str
    message: str
```