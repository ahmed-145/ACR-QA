# ACR-QA Internal API Reference

## Database API (`DATABASE/database.py`)

### `Database` Class

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `create_analysis_run` | `repo_name, commit_sha, branch, pr_number` | `int` (run ID) | Create a new analysis run |
| `complete_analysis_run` | `run_id, total_findings` | — | Mark run as complete |
| `insert_finding` | `run_id, finding_data` | `int` (finding ID) | Insert a normalized finding |
| `insert_explanation` | `finding_id, explanation_data` | `int` (explanation ID) | Insert LLM explanation with provenance |
| `get_findings_with_explanations` | `run_id` | `List[dict]` | Get all findings + explanations for a run |

## Explanation Engine (`CORE/engines/explainer.py`)

### `ExplanationEngine` Class

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `generate_explanation` | `finding, code_snippet` | `dict` | Generate RAG-grounded AI explanation |
| `get_fallback_explanation` | `finding` | `str` | Deterministic template fallback |

**Return dict keys:** `response_text`, `latency_ms`, `status`, `tokens_used`, `cost_usd`, `consistency_score`, `self_eval_score`

## Quality Gate (`CORE/engines/quality_gate.py`)

### `QualityGate` Class

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `__init__` | `config: dict` | — | Load thresholds from `.acrqa.yml` |
| `evaluate` | `findings: list[dict]` | `dict` | Evaluate findings against thresholds |
| `print_report` | `result: dict` | — | Print quality gate report to stdout |

## Config Loader (`CORE/config_loader.py`)

### `ConfigLoader` Class

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `load` | — | `dict` | Load and merge `.acrqa.yml` with defaults |
| `is_rule_enabled` | `rule_id: str` | `bool` | Check if rule is enabled |
| `get_severity_override` | `rule_id: str` | `str \| None` | Get severity override |
| `should_ignore_path` | `file_path: str` | `bool` | Check if path should be ignored |
| `get_min_severity` | — | `str` | Get minimum severity to report |
| `get_max_explanations` | — | `int` | Get max AI explanations per run |
| `generate_default_config` | `output_path: str` | `str` | Generate default `.acrqa.yml` |

## Code Extractor (`CORE/utils/code_extractor.py`)

| Function | Parameters | Returns | Description |
|----------|-----------|---------|-------------|
| `extract_code_snippet` | `file_path, line_number, context_lines=3` | `str` | Extract code with surrounding context |
| `extract_function_context` | `file_path, line_number` | `str` | Extract entire containing function |

## Pipeline CLI (`CORE/main.py`)

```bash
python3 CORE/main.py [OPTIONS]

Options:
  --target-dir DIR     Directory to analyze (default: samples/realistic-issues)
  --repo-name NAME     Repository name for provenance tracking
  --pr-number N        PR number (enables PR comment posting)
  --limit N            Max findings to explain (default: 50)
  --diff-only          Analyze only changed files
  --diff-base BRANCH   Base branch for diff (default: main)
  --auto-fix           Generate auto-fix suggestions
  --rich               Rich terminal output with tables and panels
```

## Utility Scripts

| Script | Usage | Description |
|--------|-------|-------------|
| `scripts/post_pr_comments.py` | `python3 scripts/post_pr_comments.py <RUN_ID>` | Post findings as GitHub PR comments |
| `scripts/post_gitlab_comments.py` | `python3 scripts/post_gitlab_comments.py <RUN_ID>` | Post findings as GitLab MR comments |
| `scripts/export_sarif.py` | `python3 scripts/export_sarif.py --run-id <ID>` | Export SARIF v2.1.0 |
| `scripts/export_provenance.py` | `python3 scripts/export_provenance.py <RUN_ID>` | Export full audit trail |
| `scripts/generate_report.py` | `python3 scripts/generate_report.py <RUN_ID>` | Generate Markdown report |
| `scripts/generate_pr_summary.py` | `python3 scripts/generate_pr_summary.py <RUN_ID>` | Generate PR summary |
| `scripts/generate_compliance_report.py` | `python3 scripts/generate_compliance_report.py <RUN_ID>` | Generate OWASP/SANS compliance report |
| `scripts/compute_metrics.py` | `python3 scripts/compute_metrics.py` | Compute precision/recall evaluation |
| `scripts/create_fix_pr.py` | `python3 scripts/create_fix_pr.py <RUN_ID>` | Create auto-fix PR via GitHub API |
| `scripts/user_study.py` | `python3 scripts/user_study.py` | User study tooling |