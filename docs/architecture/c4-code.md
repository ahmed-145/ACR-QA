# C4 — Code Diagram: Single Finding Lifecycle

> Level 4 of the C4 model. Traces one finding from raw tool output to PostgreSQL storage.
> Example: Bandit detects `eval(user_input)` in `app.py:42`.

```mermaid
sequenceDiagram
    participant Tool as Bandit (subprocess)
    participant Adapter as PythonAdapter
    participant Norm as Normalizer
    participant Scorer as SeverityScorer
    participant Conf as ConfidenceScorer
    participant Triage as TriageMemory
    participant Explainer as ExplanationEngine
    participant Groq as Groq API
    participant Feasibility as PathFeasibilityValidator
    participant AutoFix as AutoFixEngine
    participant DB as PostgreSQL

    Tool->>Adapter: JSON: {check_id:"B307", filename:"app.py", line:42, issue_severity:"HIGH"}
    Adapter->>Norm: normalize_bandit(bandit_json)
    Note over Norm: RULE_MAPPING["B307"] → "SECURITY-001"
    Norm->>Norm: CanonicalFinding(rule_id="SECURITY-001", file="app.py", line=42, severity="high", category="security")
    Norm->>Scorer: score("SECURITY-001", finding_dict)
    Note over Scorer: RULE_SEVERITY["SECURITY-001"] = "high" → preserved
    Scorer->>Conf: score(finding, fix_validated=False)
    Note over Conf: severity=high(40) + category=security(20) + tool=bandit(15) + rule_known(10) = 85
    Conf->>Triage: should_suppress(finding, db)
    Note over Triage: No active suppression rule matches app.py + SECURITY-001
    Triage->>Explainer: explain_batch([finding])
    Note over Explainer: RAG: retrieves rules.yml entry for SECURITY-001
    Explainer->>Explainer: _build_evidence_grounded_prompt(finding, rule_text, code_snippet)
    loop Semantic Entropy (3×)
        Explainer->>Groq: POST /openai/v1/chat/completions (Llama 3.3-70b, temp varies)
        Groq->>Explainer: explanation text
    end
    Explainer->>Explainer: compute_semantic_entropy(3 responses) → consistency_score=0.91
    Explainer->>Explainer: self_evaluate_explanation(explanation) → self_eval_score=4.2
    Explainer->>Feasibility: validate_async(finding) [HIGH only]
    Feasibility->>Groq: "Is eval(user_input) reachable from a public HTTP endpoint?"
    Groq->>Feasibility: verdict=REACHABLE, confidence=0.88
    Note over Feasibility: No penalty applied (REACHABLE)
    Feasibility->>AutoFix: generate_fix(finding)
    AutoFix->>AutoFix: fix_eval_usage(finding) → diff: eval() → ast.literal_eval()
    AutoFix->>AutoFix: verify_fix() — runs Ruff on patched code → fix_validated=True
    Note over Conf: Re-score with fix_validated=True → confidence 85 → 95
    Explainer->>DB: insert_explanation(finding_id, explanation_dict)
    Note over DB: Stores: explanation, consistency_score, self_eval_score,\nfeasibility_verdict, fix_code, fix_validated, latency_ms
    DB->>DB: insert_finding(run_id, finding_dict)
    Note over DB: Stores: canonical_rule_id="SECURITY-001", severity="high",\nfile="app.py", line=42, confidence_score=95
```

## Key data transformations

```
Raw Bandit JSON
  { "check_id": "B307",
    "filename": "/tmp/repo/app.py",
    "line_number": 42,
    "issue_severity": "HIGH",
    "issue_text": "Use of possibly insecure function - consider using safer alternatives" }

         ↓  normalize_bandit()  ↓

CanonicalFinding (Pydantic model)
  { "canonical_rule_id": "SECURITY-001",
    "file": "app.py",               ← cleaned path (not /tmp/repo/...)
    "line": 42,                     ← integer, not string
    "severity": "high",             ← lowercase, validated enum
    "category": "security",
    "message": "Use of eval() — arbitrary code execution risk (CWE-78)",
    "tool": "bandit",
    "raw_rule_id": "B307",
    "confidence_score": 95,
    "language": "python" }

         ↓  ExplanationEngine  ↓

Explanation record (PostgreSQL llm_explanations)
  { "explanation": "eval() executes arbitrary Python...",
    "consistency_score": 0.91,      ← semantic entropy across 3 LLM runs
    "self_eval_score": 4.2,         ← LLM self-rates on 1-5 scale
    "feasibility_verdict": "REACHABLE",
    "feasibility_confidence": 0.88,
    "fix_code": "value = ast.literal_eval(user_input)",
    "fix_validated": true,
    "latency_ms": 847 }
```

## Deduplication logic

When Semgrep also flags the same `eval()` at `app.py:42`:

```python
key = (finding.file, finding.line, finding.column, finding.canonical_rule_id)
# → ("app.py", 42, 15, "SECURITY-001")

# Bandit and Semgrep both produce this key.
# Tool priority: Bandit (security=3) > Semgrep (security=3) — tie → first seen wins.
# Semgrep duplicate is dropped.
```

## Performance characteristics (measured, v3.2.4)

| Stage | Typical latency | Notes |
|---|---|---|
| Tool execution (parallel) | 2–8 s | Depends on repo size |
| Normalisation | < 100 ms | Pure Python dict lookups |
| Severity scoring | < 50 ms | Dict lookups |
| AI explanation (per finding) | 300–900 ms | Groq Llama 3.3-70b |
| Semantic entropy (3× calls) | +600–1800 ms | Only for top findings |
| Path feasibility | +200–500 ms | Only for HIGH severity |
| DB insert (per finding) | < 10 ms | psycopg2 with connection reuse |
