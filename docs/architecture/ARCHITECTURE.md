# ACR-QA v2.0 Architecture

## System Overview

ACR-QA is a modular pipeline-based system for automated code review with AI-powered explanations.

## Components

### 1. Detection Layer

**Tools**:
- **Ruff**: Fast Python linter (style + best practices)
- **Semgrep**: Pattern-based security scanner
- **Vulture**: Dead code detector
- **jscpd**: Code duplication finder

**Output**: JSON files in `outputs/`

### 2. Normalization Layer

**Component**: `tools/normalize.py`

**Purpose**: Converts tool-specific outputs into unified schema

**Schema**:
```json
{
  "tool": "ruff",
  "rule_id": "F401",
  "file": "test.py",
  "line": 10,
  "column": 5,
  "severity": "warning",
  "category": "style",
  "message": "Import unused"
}
```

### 3. AI Explanation Layer

**Component**: `engines/explainer.py`

**Process**:
1. Extract code context (`utils/code_extractor.py`)
2. Build evidence-grounded prompt
3. Call Cerebras API (Llama 3.1-8b)
4. Parse and validate response
5. Fallback to template if fails

**Prompt Template**:
You are a senior Python code reviewer...
Rule ID: {rule_id}
Code Context: {snippet}
Task: Explain WHAT, WHY, HOW

### 4. Storage Layer

**Component**: `db/database.py`

**Database**: PostgreSQL 15

**Tables**:
- `analysis_runs`: Metadata for each run
- `findings`: Detected issues
- `llm_explanations`: AI-generated explanations
- `pr_comments`: Posted comments
- `feedback`: User feedback

### 5. Integration Layer

**Components**:
- `scripts/post_comments.py`: GitHub API
- `scripts/post_comments_gitlab.py`: GitLab API

**Flow**:
1. Trigger on PR/MR event
2. Run analysis
3. Post top N findings as comments
4. Log all actions to database

### 6. Reporting Layer

**Components**:
- `scripts/dashboard.py`: Interactive CLI
- `scripts/generate_report.py`: Markdown export
- `scripts/export_provenance.py`: JSON audit trail

## Data Flow
[Code Repository]
↓
[Detection Tools] → outputs/*.json
↓
[Normalizer] → outputs/findings.json
↓
[Main Pipeline] → Database
↓                ↓
[AI Explainer]   [PR Commenter]
↓                ↓
[Dashboard/Reports]  [GitHub/GitLab]

## Technology Stack

- **Language**: Python 3.11
- **Database**: PostgreSQL 15
- **AI**: Cerebras API (Llama 3.1-8b)
- **CI/CD**: GitHub Actions, GitLab CI
- **Containers**: Docker, Docker Compose
- **Testing**: pytest
- **CLI**: Rich library

## Scalability Considerations

- **Batch Processing**: Limit findings per run
- **Async API**: Use tenacity for retries
- **Database Indexing**: Optimized queries
- **Caching**: Code snippets cached in memory

## Security

- **Secrets**: Environment variables only
- **API Keys**: Never logged or committed
- **Database**: Parameterized queries (no SQL injection)
- **Docker**: Non-root user in containers