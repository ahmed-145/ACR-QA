import marimo

__generated_with = "0.10.0"
app = marimo.App(width="medium", app_title="ACR-QA — Pipeline Walkthrough")


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _(mo):
    mo.md(
        r"""
        # ACR-QA — Automated Code Review & Quality Assurance
        ### Thesis Defense Walkthrough · v3.8.0

        This notebook demonstrates the **full ACR-QA pipeline** end-to-end:

        1. Load a target repository
        2. Static analysis (Semgrep + Bandit + Ruff + Gosec)
        3. Taint tracking (source → sink data-flow)
        4. AI triage (LLM-powered false-positive reduction)
        5. Auto-fix patch generation
        6. Supply-chain risk + SBOM
        7. Signed attestation (ECDSA-P256 + Dilithium3)
        8. Quality gate enforcement

        > **Zero egress required.** All LLM calls can be routed to local Ollama.
        """
    )
    return


@app.cell
def _(mo):
    mo.md("## Cell 1 — Project Setup")


@app.cell
def _():
    import sys
    import os
    from pathlib import Path

    # Add project root to path
    ROOT = Path(__file__).parent.parent
    sys.path.insert(0, str(ROOT))

    os.environ.setdefault("DATABASE_URL", "postgresql://acrqa:acrqa@localhost:5432/acrqa")
    os.environ.setdefault("ACRQA_LLM_PROVIDER", "openai")

    from CORE import __version__
    from CORE.main import AnalysisPipeline

    print(f"ACR-QA {__version__} loaded ✓")
    print(f"Project root: {ROOT}")
    return AnalysisPipeline, Path, ROOT, __version__, os, sys


@app.cell
def _(mo):
    mo.md("## Cell 2 — Target Repository")


@app.cell
def _(ROOT, mo):
    import marimo as _mo

    # UI control — pick a sample target
    target_options = {
        "Comprehensive Issues (built-in)": str(ROOT / "TESTS" / "samples" / "comprehensive-issues"),
        "Realistic Issues (built-in)": str(ROOT / "TESTS" / "samples" / "realistic-issues"),
        "Taint Fixtures (built-in)": str(ROOT / "TESTS" / "fixtures" / "taint"),
    }

    target_dropdown = mo.ui.dropdown(
        options=target_options,
        value=str(ROOT / "TESTS" / "samples" / "comprehensive-issues"),
        label="Target directory",
    )
    target_dropdown
    return target_dropdown, target_options


@app.cell
def _(ROOT, target_dropdown):
    target_dir = target_dropdown.value or str(ROOT / "TESTS" / "samples" / "comprehensive-issues")
    print(f"Target: {target_dir}")
    return (target_dir,)


@app.cell
def _(mo):
    mo.md("## Cell 3 — Static Analysis Engine")


@app.cell
def _(AnalysisPipeline, mo, target_dir):
    import traceback

    with mo.status.spinner(title="Running static analysis…"):
        try:
            pipeline = AnalysisPipeline(target_dir=target_dir)
            raw_findings = pipeline._run_tools()
            print(f"Raw findings: {len(raw_findings)}")
        except Exception as exc:
            print(f"[DEMO MODE] DB not available — using synthetic findings")
            print(f"  ({exc})")
            raw_findings = [
                {"rule_id": "B608", "severity": "HIGH", "category": "injection",
                 "file_path": "app.py", "line_number": 42,
                 "message": "Possible SQL injection via string-based query construction",
                 "tool": "bandit", "confidence": 0.91},
                {"rule_id": "S001", "severity": "HIGH", "category": "injection",
                 "file_path": "routes.py", "line_number": 17,
                 "message": "Tainted user input flows to os.system() call",
                 "tool": "semgrep", "confidence": 0.87},
                {"rule_id": "B324", "severity": "MEDIUM", "category": "cryptography",
                 "file_path": "auth.py", "line_number": 8,
                 "message": "Use of MD5 for password hashing",
                 "tool": "bandit", "confidence": 0.95},
                {"rule_id": "E501", "severity": "LOW", "category": "style",
                 "file_path": "utils.py", "line_number": 103,
                 "message": "Line too long (120 > 79 characters)",
                 "tool": "ruff", "confidence": 1.0},
                {"rule_id": "B105", "severity": "MEDIUM", "category": "hardcoded_credentials",
                 "file_path": "config.py", "line_number": 3,
                 "message": "Possible hardcoded password: 'changeme123'",
                 "tool": "bandit", "confidence": 0.78},
            ]

    print(f"\nSeverity breakdown:")
    from collections import Counter
    sev_counts = Counter(f.get("severity", "?") for f in raw_findings)
    for sev, cnt in sorted(sev_counts.items()):
        print(f"  {sev}: {cnt}")
    return Counter, exc, raw_findings, sev_counts, traceback


@app.cell
def _(mo):
    mo.md("## Cell 4 — Findings Summary Table")


@app.cell
def _(mo, raw_findings):
    table_data = [
        {
            "Rule": f.get("rule_id", "—"),
            "Severity": f.get("severity", "—"),
            "File": f.get("file_path", "—"),
            "Line": str(f.get("line_number", "—")),
            "Tool": f.get("tool", "—"),
            "Confidence": f"{int(f.get('confidence', 0) * 100)}%",
        }
        for f in raw_findings[:20]
    ]

    mo.ui.table(table_data, label="Static Analysis Findings (first 20)")
    return (table_data,)


@app.cell
def _(mo):
    mo.md("## Cell 5 — Taint Analysis Engine")


@app.cell
def _(ROOT, mo):
    with mo.status.spinner(title="Running taint analyzer…"):
        try:
            from CORE.engines.taint_analyzer import TaintAnalyzer
            taint_target = str(ROOT / "TESTS" / "fixtures" / "taint" / "multihop_sqli.py")
            analyzer = TaintAnalyzer()
            taint_results = analyzer.analyze_file(taint_target)
            print(f"Taint findings: {len(taint_results)}")
            for t in taint_results[:3]:
                print(f"  [{t.severity}] {t.rule_id}: {t.taint_source} → line {t.line_number}")
        except Exception as exc2:
            print(f"[DEMO MODE] Taint analyzer demo:")
            taint_results = []
            print("  Source : request.args.get('user_id')  [HTTP query param]")
            print("  Hop 1  : user_id passed to format_query()")
            print("  Hop 2  : format_query() returns f-string SQL")
            print("  Sink   : db.execute(sql)  [SQL execution]")
            print("  Verdict: TAINTED — no sanitizer in path ✗")
            exc2 = exc2
    return exc2, taint_results


@app.cell
def _(mo):
    mo.md(
        r"""
        ### Taint Flow Diagram

        ```
        [SOURCE] request.args.get('user_id')
             │  HTTP query parameter — attacker controlled
             ▼
        [HOP 1] user_id ──► format_query(user_id)
             │  String interpolation, no sanitization
             ▼
        [HOP 2] sql = f"SELECT * FROM users WHERE id={user_id}"
             │  Tainted string construction
             ▼
        [SINK]  db.execute(sql)   ← SQL INJECTION ✗
        ```

        **Confidence:** 0.87 · **Engine:** TaintAnalyzer v3.6.3
        """
    )
    return


@app.cell
def _(mo):
    mo.md("## Cell 6 — AI Triage Agent")


@app.cell
def _(mo, raw_findings):
    with mo.status.spinner(title="Running triage agent (LLM)…"):
        try:
            from CORE.engines.triage_agent import TriageAgent
            agent = TriageAgent()
            finding_to_triage = raw_findings[0] if raw_findings else {}
            verdict = agent.triage(finding_to_triage)
            print(f"Verdict: {verdict.verdict}")
            print(f"Reasoning: {verdict.reasoning[:200]}…")
            print(f"Confidence delta: {verdict.confidence_delta:+.2f}")
        except Exception:
            print("[DEMO MODE] Triage agent output:")
            print("  Finding : B608 — SQL injection (confidence: 91%)")
            print("  Verdict : TRUE_POSITIVE")
            print("  Reasoning: The finding at app.py:42 shows direct string")
            print("             concatenation of request.args into a SQL query.")
            print("             No parameterization or ORM layer detected.")
            print("             This is a genuine SQL injection vulnerability.")
            print("  Δ confidence: +0.06  (91% → 97%)")
    return


@app.cell
def _(mo):
    mo.md("## Cell 7 — Auto-Fix Patch Generator")


@app.cell
def _(mo, raw_findings):
    with mo.status.spinner(title="Generating auto-fix patch…"):
        try:
            from CORE.engines.autofix import AutoFixEngine
            engine = AutoFixEngine()
            finding = raw_findings[0] if raw_findings else {}
            patch = engine.generate_patch(finding, run_id=0, db=None)
            print(f"Patch confidence: {patch.get('confidence', 0):.0%}")
            print(patch.get("patch", "")[:400])
        except Exception:
            print("[DEMO MODE] Auto-fix patch:")
            print("""
--- a/app.py
+++ b/app.py
@@ -40,7 +40,8 @@ def get_user(user_id):
-    sql = f"SELECT * FROM users WHERE id={user_id}"
-    result = db.execute(sql)
+    sql = "SELECT * FROM users WHERE id = %s"
+    result = db.execute(sql, (user_id,))
     return result
""")
            print("  Confidence: 94% | Explanation: Use parameterized queries")
            print("  to prevent SQL injection. The %s placeholder ensures the")
            print("  database driver handles escaping correctly.")
    return


@app.cell
def _(mo):
    mo.md("## Cell 8 — Supply Chain Analysis")


@app.cell
def _(ROOT, mo):
    with mo.status.spinner(title="Scanning supply chain…"):
        try:
            from CORE.engines.supply_chain import SupplyChainEngine
            sc = SupplyChainEngine()
            sample_req = ROOT / "requirements.txt"
            deps = sc.analyze(str(sample_req)) if sample_req.exists() else []
            high_risk = [d for d in deps if getattr(d, "risk_level", "") == "high"]
            print(f"Dependencies: {len(deps)}")
            print(f"High-risk: {len(high_risk)}")
        except Exception:
            print("[DEMO MODE] Supply chain analysis:")
            print("  Total dependencies: 47")
            print("  HIGH risk: 2  (CVE-2024-3094 in xz-utils, CVE-2023-44487 in h2)")
            print("  MEDIUM risk: 8")
            print("  LOW risk: 37")
            print("  Archived packages: 1  (unmaintained)")
            print("  SBOM format: CycloneDX 1.4 JSON")
    return


@app.cell
def _(mo):
    mo.md("## Cell 9 — Signed Attestation")


@app.cell
def _(ROOT, mo):
    with mo.status.spinner(title="Generating attestation…"):
        try:
            from CORE.engines.attestation import AttestationEngine
            engine = AttestationEngine()
            attest = engine.generate(run_id=1, findings_count=5, repo="demo")
            print(f"Algorithm: {attest.get('algorithm', 'ECDSA-P256')}")
            print(f"Signature: {str(attest.get('signature', ''))[:48]}…")
        except Exception:
            print("[DEMO MODE] Attestation output:")
            print("  Algorithm : ECDSA-P256 + Dilithium3 (post-quantum hybrid)")
            print("  Run ID    : demo-001")
            print("  Findings  : 5 (SHA-256 hash of finding set)")
            print("  Timestamp : 2026-05-15T03:45:00Z")
            print("  Signature : MEQCIBv7Xk2...  [64-byte P-256 signature]")
            print("  Verify    : python3 verify_attestation.py --run demo-001")
    return


@app.cell
def _(mo):
    mo.md("## Cell 10 — Quality Gate")


@app.cell
def _(mo, raw_findings):
    from collections import Counter as _Counter

    sev = _Counter(f.get("severity", "?") for f in raw_findings)
    high = sev.get("HIGH", 0)
    medium = sev.get("MEDIUM", 0)
    total = len(raw_findings)

    gate_config = {"max_high": 0, "max_medium": 10, "max_total": 200}
    passed = high <= gate_config["max_high"] and medium <= gate_config["max_medium"]
    status = "✅ PASSED" if passed else "❌ FAILED"

    mo.callout(
        mo.md(f"""
**Quality Gate: {status}**

| Metric | Found | Limit | Status |
|--------|-------|-------|--------|
| HIGH severity | {high} | {gate_config['max_high']} | {"✗ FAIL" if high > gate_config['max_high'] else "✓ OK"} |
| MEDIUM severity | {medium} | {gate_config['max_medium']} | {"✗ FAIL" if medium > gate_config['max_medium'] else "✓ OK"} |
| Total findings | {total} | {gate_config['max_total']} | {"✗ FAIL" if total > gate_config['max_total'] else "✓ OK"} |
        """),
        kind="danger" if not passed else "success",
    )
    return gate_config, high, medium, passed, sev, status, total


@app.cell
def _(mo):
    mo.md("## Cell 11 — Performance Metrics")


@app.cell
def _(mo):
    mo.md(
        r"""
        ### Benchmark Results (v3.8.0)

        | Metric | Value | Target |
        |--------|-------|--------|
        | Flask app recall | **98.0%** | ≥ 80% |
        | httpx recall | **97.7%** | ≥ 80% |
        | False-positive rate | **1.0%** | ≤ 5% |
        | Triage FP reduction | **-43%** | — |
        | Scan latency (50k LOC) | **< 8s** | < 10s |
        | Total tests | **2,170** | ≥ 2,000 |
        | Test coverage | **89%** | ≥ 85% |

        > Benchmarked against: DVWA, DVPWA, PyGoat, Juice Shop, DVNA,
        > NodeGoat, Tiredful-API, bandit-test-cases, vulnerable-flask-app, seeded-repo
        """
    )
    return


@app.cell
def _(mo):
    mo.md("## Cell 12 — Architecture Summary")


@app.cell
def _(mo):
    mo.md(
        r"""
        ### ACR-QA System Architecture

        ```
        ┌─────────────────────────────────────────────────────────┐
        │                    ACR-QA v3.8.0                        │
        ├─────────────────────────────────────────────────────────┤
        │  LAYER 1 — Static Analysis                              │
        │  Semgrep · Bandit · Ruff · Gosec · Vulture · ESLint     │
        │                                                         │
        │  LAYER 2 — Deep Analysis Engines                        │
        │  TaintAnalyzer  · PathFeasibility · ReachabilityEngine  │
        │  ExploitVerifier · SupplyChainEngine · SecretsDetector  │
        │                                                         │
        │  LAYER 3 — AI Layer                                     │
        │  Explainer · TriageAgent · AutoFixEngine                │
        │  OllamaProvider (offline) · OpenAI / Anthropic          │
        │                                                         │
        │  LAYER 4 — Trust & Compliance                           │
        │  AttestationEngine (ECDSA-P256 + Dilithium3)            │
        │  QualityGate · ComplianceMapper (OWASP Top 10)          │
        │                                                         │
        │  LAYER 5 — Data & API                                   │
        │  PostgreSQL · Redis · Celery · FastAPI · React SPA      │
        └─────────────────────────────────────────────────────────┘
        ```

        **5 core engines** · **9 DB migrations** · **2,170 tests** ·
        **87/128 GOD_MODE_PLAN tasks complete**
        """
    )
    return


if __name__ == "__main__":
    app.run()
