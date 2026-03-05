# ACR-QA Policy Engine

ACR-QA uses a **policy-as-code** approach — your project's analysis behavior is entirely controlled by the `.acrqa.yml` configuration file in your project root. No GUI needed, no admin panels. Commit the policy with your code, review it in PRs, version it in git.

---

## How It Works

```
.acrqa.yml → ConfigLoader → Analysis Pipeline → Quality Gate → Pass/Fail
                                  ↑                     ↑
                           Severity Overrides    Threshold Checks
                           Rule Suppression      Security Gate
                           Path Exclusions       Test Gap Gate
```

The policy file controls **what gets scanned**, **what severity gets reported**, **which rules are enforced**, and **what thresholds block CI/CD merges**.

---

## Policy Sections

### 1. Rule Suppression

Disable specific rules that don't apply to your project:

```yaml
rules:
  disabled_rules:
    - IMPORT-001   # We use wildcard imports intentionally
    - STYLE-003    # Naming convention doesn't match our codebase
```

**Enforced by:** `ConfigLoader.is_rule_enabled()` → `AnalysisPipeline._apply_config_filters()`

### 2. Severity Overrides

Override the default severity of any rule. For example, if your project treats unused variables as critical:

```yaml
rules:
  severity_overrides:
    VAR-001: high     # Unused variables are unacceptable here
    STYLE-001: low    # Naming is a suggestion, not a rule
```

**Enforced by:** `ConfigLoader.get_severity_override()` → applied before quality gate evaluation

### 3. Path Exclusions

Exclude files/directories from analysis:

```yaml
analysis:
  ignore_paths:
    - __pycache__
    - .venv
    - node_modules
    - "migrations/*"
    - "*.generated.py"
```

**Enforced by:** `ConfigLoader.should_ignore_path()`

### 4. Minimum Severity Filter

Suppress all findings below a certain severity level:

```yaml
reporting:
  min_severity: medium   # Only show medium and high findings
```

**Enforced by:** `AnalysisPipeline._apply_config_filters()`

### 5. Quality Gate (CI/CD Blocker)

Define thresholds that **fail the CI/CD pipeline** when exceeded:

```yaml
quality_gate:
  max_high: 0        # Zero tolerance for high-severity findings
  max_medium: 5      # No more than 5 medium issues
  max_total: 50      # Cap total findings
  max_security: 0    # Zero tolerance for security findings
```

**Enforced by:** `QualityGate.evaluate()` → returns pass/fail with per-check details

### 6. Autofix Policy

Control whether auto-fixes are generated and applied:

```yaml
autofix:
  enabled: true
  auto_apply_confidence: 80  # Only auto-apply fixes >= 80% confidence
```

### 7. AI Explanation Policy

Control the AI explanation engine:

```yaml
ai:
  enabled: true
  max_explanations: 50
  model: llama-3.1-8b-instant
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|:------:|-------------|
| `/api/policy` | GET | Returns the active policy configuration as JSON |
| `/api/test-gaps` | GET | Test gap analysis results |
| `/api/runs/<id>/compliance` | GET | OWASP Top 10 compliance report |

---

## CLI Tools

| Tool | Command | Description |
|------|---------|-------------|
| **Config Validator** | `python scripts/validate_config.py validate .acrqa.yml` | Validates your policy file against the schema |
| **Template Generator** | `python scripts/validate_config.py template` | Generates a documented template with all options |
| **Test Gap Analyzer** | `python scripts/test_gap_analyzer.py --target CORE/` | Finds untested functions/classes |
| **Feedback Tuner** | `python scripts/feedback_tuner.py --apply` | Auto-generates severity overrides from FP feedback |
| **Compliance Report** | `python scripts/generate_compliance_report.py` | OWASP Top 10 compliance mapping |

---

## Generating a Template

```bash
python scripts/validate_config.py template -o .acrqa.yml
```

This generates a fully documented `.acrqa.yml` with all available options and their defaults.

---

## Validating Your Policy

```bash
python scripts/validate_config.py validate .acrqa.yml
```

Output:
```
🔍 Validating .acrqa.yml...
  ⚠️  Unknown key 'version' — will be ignored.
  ✅ Configuration is valid!
```

The validator catches:
- Unknown keys (typos)
- Type mismatches (e.g., setting a boolean where a string is expected)
- Invalid severity values
- Unknown sub-keys
