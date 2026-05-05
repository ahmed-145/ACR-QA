# C3 — Component Diagram

> Level 3 of the C4 model. Shows the major components inside the Analysis Engine container.

```mermaid
C4Component
    title ACR-QA — Analysis Engine Components

    Container_Boundary(core, "Analysis Engine (CORE/)") {

        Component(pipeline, "AnalysisPipeline", "Python class", "Orchestrates the full pipeline. Entry point from CLI. Calls adapters, extra scanners, normaliser, scorer, gate, explainer, DB.")

        Component_Boundary(adapters, "Language Adapters") {
            Component(py_adapter, "PythonAdapter", "Python", "Runs Ruff, Bandit, Semgrep, Vulture, Radon via run_checks.sh")
            Component(js_adapter, "JavaScriptAdapter", "Python", "Runs ESLint (security plugin), Semgrep JS rules, npm audit")
            Component(go_adapter, "GoAdapter", "Python", "Runs gosec, staticcheck, Semgrep Go rules")
        }

        Component_Boundary(scanners, "Extra Scanners") {
            Component(secrets, "SecretsDetector", "Python", "Regex-based detection of API keys, passwords, JWTs, tokens")
            Component(sca, "SCAScanner", "Python", "pip-audit — maps CVEs to SECURITY-034..038")
            Component(cbom, "CBoMScanner", "Python", "Inventories crypto APIs, classifies by quantum-safety per NIST FIPS 203/204")
        }

        Component_Boundary(engines, "Core Engines") {
            Component(normalizer, "Normalizer", "Python", "311 rule mappings: tool-specific code → canonical ID (SECURITY-xxx, STYLE-xxx). Produces CanonicalFinding Pydantic models.")
            Component(scorer, "SeverityScorer", "Python", "RULE_SEVERITY dict: canonical ID → high/medium/low. Context-aware overrides.")
            Component(gate, "QualityGate", "Python", "Evaluates max_high/medium/total/security thresholds from .acrqa.yml. Returns exit code 1 on violation.")
            Component(confidence, "ConfidenceScorer", "Python", "0-100 score per finding. 5 signals: severity, category, tool reliability, rule specificity, fix validated.")
            Component(dedup, "Deduplicator", "Python", "Cross-tool dedup by (file, line, column, rule_id). Tool priority: security > specialised > general.")
        }

        Component_Boundary(advanced, "Advanced Engines") {
            Component(triage, "TriageMemory", "Python", "Learns FP patterns from user feedback. Suppresses matching findings in future scans.")
            Component(feasibility, "PathFeasibilityValidator", "Python", "LLM-based path reachability check for HIGH findings. Inspired by LLM4PFA (arXiv).")
            Component(correlator, "CrossLanguageCorrelator", "Python", "Detects vulnerability chains across Python/Jinja2/JS layers. Inspired by CHARON (CISPA/NDSS).")
            Component(reachability, "DependencyReachability", "Python", "Classifies vulnerable npm packages as DIRECT/TRANSITIVE/UNKNOWN based on actual imports.")
        }

        Component_Boundary(ai, "AI Layer") {
            Component(explainer, "ExplanationEngine", "Python + httpx async", "RAG: retrieves rule from rules.yml KB → builds evidence-grounded prompt → calls Groq LLM. Entropy scoring (3x). Self-evaluation (1-5).")
            Component(autofix, "AutoFixEngine", "Python", "Generates before/after diffs for 8 fixable rule categories. Verifies fix by re-running Ruff.")
        }

        Component(config_loader, "ConfigLoader", "Python", "Reads .acrqa.yml. Exposes: is_rule_enabled(), get_severity_override(), should_ignore_path().")
    }

    Rel(pipeline, py_adapter, "Calls for Python repos")
    Rel(pipeline, js_adapter, "Calls for JS/TS repos")
    Rel(pipeline, go_adapter, "Calls for Go repos")
    Rel(pipeline, secrets, "Always runs")
    Rel(pipeline, sca, "Always runs")
    Rel(pipeline, cbom, "Always runs")
    Rel(py_adapter, normalizer, "Raw tool JSON → CanonicalFindings")
    Rel(js_adapter, normalizer, "Raw tool JSON → CanonicalFindings")
    Rel(go_adapter, normalizer, "Raw tool JSON → CanonicalFindings")
    Rel(normalizer, scorer, "Assigns severity")
    Rel(scorer, confidence, "Scores 0-100")
    Rel(confidence, dedup, "Deduplicates cross-tool")
    Rel(dedup, triage, "Suppresses known FPs")
    Rel(triage, gate, "Applies thresholds")
    Rel(gate, explainer, "Explains high-priority findings")
    Rel(explainer, feasibility, "Validates HIGH finding paths")
    Rel(explainer, autofix, "Generates + verifies fixes")
    Rel(pipeline, config_loader, "Reads policy at startup")
    Rel(pipeline, correlator, "Enriches with cross-language chains")
    Rel(js_adapter, reachability, "Checks npm package import status")
```

## Component interaction sequence (single Python scan)

```
CLI args
  └─► AnalysisPipeline.run()
        ├─► ConfigLoader.load()              — reads .acrqa.yml
        ├─► RateLimiter.check()              — Redis: 1 scan/repo/min
        ├─► DB.create_analysis_run()
        ├─► PythonAdapter.run_tools()        — parallel: Ruff + Bandit + Semgrep + Vulture + Radon
        ├─► run_extra_scanners()             — SecretsDetector + SCAScanner + CBoMScanner
        ├─► Normalizer.normalize_all()       — 311 rule mappings → CanonicalFindings
        ├─► SeverityScorer.score()           — per-finding severity
        ├─► ConfigLoader.apply_filters()     — ignore_paths, disabled_rules, min_severity
        ├─► TriageMemory.suppress_findings() — DB-backed FP suppression
        ├─► dedup()                          — cross-tool by (file, line, column, rule_id)
        ├─► per_rule_cap(5)                  — prevents noisy rules from dominating
        ├─► sort(HIGH → MEDIUM → LOW)
        ├─► CrossLanguageCorrelator.enrich() — confidence boosts for chains
        ├─► ConfidenceScorer.score_batch()   — 0-100 per finding
        ├─► ExplanationEngine.batch()        — async Groq calls (RAG + entropy + self-eval)
        │     └─► PathFeasibilityValidator   — second AI call for HIGH findings
        ├─► AutoFixEngine.generate_fix()     — diffs for fixable rules
        ├─► QualityGate.evaluate()           — pass/fail; exit code 1 on block
        └─► DB.insert_finding() × N          — full provenance stored
```
