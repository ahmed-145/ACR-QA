# ACR-QA API Reference

## Database API

### `Database` Class

#### Methods

##### `create_analysis_run(repo_name, commit_sha=None, branch=None, pr_number=None)`
Create a new analysis run.

**Returns**: `int` - Run ID

##### `complete_analysis_run(run_id, total_findings)`
Mark an analysis run as complete.

##### `insert_finding(run_id, finding_data)`
Insert a finding into the database.

**Parameters**:
- `finding_data` (dict): Must contain `tool`, `rule_id`, `file`, `line`, `severity`, `category`, `message`

**Returns**: `int` - Finding ID

##### `insert_explanation(finding_id, explanation_data)`
Insert an LLM explanation.

**Parameters**:
- `explanation_data` (dict): Must contain `model_name`, `prompt_template`, `prompt_filled`, `response_text`, `temperature`, `max_tokens`, `latency_ms`

**Returns**: `int` - Explanation ID

##### `get_findings_with_explanations(run_id)`
Get all findings with their explanations for a run.

**Returns**: `List[dict]`

## Explanation Engine API

### `ExplanationEngine` Class

#### Methods

##### `generate_explanation(finding, code_snippet="")`
Generate AI explanation for a finding.

**Parameters**:
- `finding` (dict): Finding data
- `code_snippet` (str): Code context

**Returns**: `dict` with keys:
- `response_text`: Generated explanation
- `latency_ms`: API latency
- `status`: 'success' or 'failed'
- `tokens_used`: Number of tokens
- `cost_usd`: Estimated cost

##### `get_fallback_explanation(finding)`
Get deterministic fallback explanation.

**Returns**: `str`

## Code Extractor API

### Functions

##### `extract_code_snippet(file_path, line_number, context_lines=3)`
Extract code snippet with context.

**Returns**: `str` - Formatted code snippet

##### `extract_function_context(file_path, line_number)`
Extract entire function containing the line.

**Returns**: `str` - Formatted function code

## CLI Scripts

### `main.py`
```bash
python main.py [OPTIONS]

Options:
  --target-dir TEXT      Directory to analyze (default: samples/seeded-repo)
  --repo-name TEXT       Repository name (default: local)
  --pr-number INTEGER    Pull request number
  --limit INTEGER        Limit explanations (default: 10)
```

### `scripts/dashboard.py`
```bash
python scripts/dashboard.py [--run-id INTEGER]
```

### `scripts/generate_report.py`
```bash
python scripts/generate_report.py RUN_ID [--output-dir TEXT]
```

### `scripts/collect_feedback.py`
```bash
python scripts/collect_feedback.py RUN_ID [--user-id TEXT] [--limit INTEGER]
```

### `scripts/export_provenance.py`
```bash
python scripts/export_provenance.py RUN_ID [--output-dir TEXT]
```