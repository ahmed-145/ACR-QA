# ACR-QA Canonical Finding Schema

All findings are normalized to this universal format:
```json
{
  "finding_id": "uuid-here",
  "rule_id": "SOLID-001",           // Universal rule ID
  "severity": "high|medium|low",    // Normalized (not error/warning/info)
  "category": "design|security|style|duplication|unused",
  "file": "path/to/file.py",
  "line": 42,
  "language": "python",
  "evidence": {
    "snippet": "def foo(a, b, c, d, e, f, g):",
    "context_before": ["# Previous lines", "class MyClass:"],
    "context_after": ["    pass", ""]
  },
  "tool_raw": {
    "tool_name": "ruff",
    "original_output": {...}  // Preserved for audit
  }
}
```