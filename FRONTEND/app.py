#!/usr/bin/env python3
"""
ACR-QA v3.2.4 Web Dashboard
Flask + Tailwind CSS
"""

import logging
import os
import sys
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

sys.path.insert(0, str(Path(__file__).parent.parent))

from CORE.utils.metrics import register_metrics_endpoint, track_request
from DATABASE.database import Database

logger = logging.getLogger(__name__)


app = Flask(__name__)
CORS(app)
# Security: Use environment variable for SECRET_KEY, fallback to random per-instance key
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", os.urandom(32).hex())

# Register Prometheus /metrics endpoint for observability
register_metrics_endpoint(app)

db = Database()


@app.errorhandler(Exception)
def handle_global_error(e):
    """Global exception handler for all unhandled errors."""
    if isinstance(e, HTTPException):
        return jsonify({"success": False, "error": e.description}), e.code
    logger.error(f"Unhandled exception: {e}", exc_info=True)
    return jsonify({"success": False, "error": str(e)}), 500


def _calculate_confidence(finding):
    """
    Fallback heuristic confidence calculation for legacy data.

    Factors:
    - Rule citation in explanation: +0.2
    - High severity: +0.1
    - Security category: +0.1
    - Has explanation: +0.1
    - Default baseline: 0.5
    """
    score = 0.5

    explanation = finding.get("explanation_text", "") or ""
    rule_id = finding.get("canonical_rule_id", "") or ""
    severity = finding.get("canonical_severity", "low")
    category = finding.get("category", "")

    # Rule is cited in explanation → high confidence
    if rule_id and rule_id in explanation:
        score += 0.2

    # Has an explanation at all → some confidence
    if explanation:
        score += 0.1

    # High severity findings are more likely to be real
    if severity == "high":
        score += 0.1

    # Security findings are more likely to be real
    if category == "security":
        score += 0.1

    return min(1.0, round(score, 2))


@app.route("/")
def index():
    """Main dashboard page"""
    return render_template("index.html")


@app.route("/api/runs")
def get_runs():
    """Get recent analysis runs"""
    try:
        limit = request.args.get("limit", 10, type=int)
        runs = db.get_recent_runs(limit=limit)

        # Add summary for each run
        runs_with_summary = []
        for run in runs:
            summary = db.get_run_summary(run["id"])
            runs_with_summary.append(
                {
                    "id": run["id"],
                    "repo_name": run["repo_name"],
                    "pr_number": run.get("pr_number"),
                    "status": run["status"],
                    "started_at": str(run["started_at"]),
                    "total_findings": summary.get("findings_count", 0) if summary else 0,
                    "high_count": summary.get("high_severity_count", 0) if summary else 0,
                    "medium_count": summary.get("medium_severity_count", 0) if summary else 0,
                    "low_count": summary.get("low_severity_count", 0) if summary else 0,
                }
            )

        return jsonify({"success": True, "runs": runs_with_summary})
    except Exception as e:
        logger.error(f"Error in /api/runs: {e}")

        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/runs/<int:run_id>/findings")
def get_run_findings(run_id):
    """Get findings for a specific run with filters"""
    try:
        severity = request.args.get("severity")
        category = request.args.get("category")
        search = request.args.get("search", "").lower()
        group_by = request.args.get("group_by")  # New: 'rule' for grouping
        min_confidence = request.args.get("min_confidence", type=float)

        # Get findings
        findings = db.get_findings_with_explanations(run_id)

        # Apply filters
        filtered = []
        for f in findings:
            # Severity filter
            if severity and f.get("canonical_severity") != severity:
                continue

            # Category filter
            if category and f.get("category") != category:
                continue

            # Search filter
            if search:
                searchable = f"{f.get('file_path', '')} {f.get('message', '')} {f.get('canonical_rule_id', '')}".lower()
                if search not in searchable:
                    continue

            # Calculate confidence score
            db_conf = f.get("confidence_score")
            confidence = db_conf if db_conf is not None else _calculate_confidence(f)

            # Confidence filter (noise control)
            if min_confidence is not None and confidence < min_confidence:
                continue

            filtered.append(
                {
                    "id": f["id"],
                    "rule_id": f.get("canonical_rule_id", f.get("rule_id")),
                    "severity": f.get("canonical_severity", "low"),
                    "category": f.get("category"),
                    "file_path": f.get("file_path"),
                    "line_number": f.get("line_number"),
                    "message": f.get("message"),
                    "explanation_text": f.get("explanation_text"),
                    "model_name": f.get("model_name"),
                    "latency_ms": f.get("latency_ms"),
                    "tool": f.get("tool"),
                    "confidence": confidence,
                    "ground_truth": f.get("ground_truth"),  # For Phase 2 evaluation
                }
            )

        # Polish: Group by rule if requested
        if group_by == "rule":
            grouped = {}
            for f in filtered:
                rule_id = f["rule_id"]
                if rule_id not in grouped:
                    grouped[rule_id] = {
                        "rule_id": rule_id,
                        "count": 0,
                        "severity": f["severity"],
                        "category": f["category"],
                        "findings": [],
                    }
                grouped[rule_id]["count"] += 1
                grouped[rule_id]["findings"].append(f)

            return jsonify(
                {
                    "success": True,
                    "grouped": True,
                    "groups": list(grouped.values()),
                    "total": len(filtered),
                }
            )

        return jsonify({"success": True, "findings": filtered, "total": len(filtered)})
    except Exception as e:
        logger.error(f"Error in /api/runs/{run_id}/findings: {e}")

        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/runs/<int:run_id>/stats")
def get_run_stats(run_id):
    """Get statistics for a run"""
    try:
        summary = db.get_run_summary(run_id)

        if not summary:
            return jsonify({"success": False, "error": "Run not found"}), 404

        return jsonify(
            {
                "success": True,
                "run_id": run_id,
                "repo_name": summary.get("repo_name"),
                "status": summary.get("status"),
                "total_findings": summary.get("findings_count", 0),
                "high": summary.get("high_severity_count", 0),
                "medium": summary.get("medium_severity_count", 0),
                "low": summary.get("low_severity_count", 0),
                "explanations_count": summary.get("explanations_count", 0),
                "avg_latency_ms": float(summary.get("avg_explanation_latency", 0) or 0),
                "total_cost_usd": float(summary.get("total_cost", 0) or 0),
            }
        )
    except Exception as e:
        logger.error(f"Error in /api/runs/{run_id}/stats: {e}")

        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/categories")
def get_categories():
    """Get all available categories across all runs"""
    try:
        # Get categories from all findings, not just latest run
        findings = db.get_findings(limit=1000)
        categories = sorted(set(f["category"] for f in findings if f.get("category")))

        return jsonify({"success": True, "categories": categories})
    except Exception as e:
        logger.error(f"Error in /api/categories: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/refresh-findings", methods=["POST"])
def refresh_findings():
    """
    Quick Refresh: Re-run detection tools and update database
    WITHOUT generating AI explanations (fast refresh for development)

    This solves the synchronization issue where tool outputs are updated
    but the database still has old data.
    """
    import json as json_module
    import subprocess
    from pathlib import Path as PathLib

    try:
        # Get parameters
        data = request.get_json() or {}
        target_dir = data.get("target_dir", "TESTS/samples/comprehensive-issues")
        repo_name = data.get("repo_name", "quick-refresh")
        skip_detection = data.get("skip_detection", False)  # Re-use existing tool outputs

        project_root = PathLib(__file__).parent.parent

        # Step 1: Run detection tools (unless skipped)
        if not skip_detection:
            subprocess.run(
                ["bash", "TOOLS/run_checks.sh", target_dir],
                cwd=str(project_root),
                check=True,
                capture_output=True,
            )

        # Step 2: Normalize findings
        from CORE.engines.normalizer import normalize_all

        findings = normalize_all(project_root / "DATA" / "outputs")

        # Step 3: Create a new run in database
        run_id = db.create_analysis_run(repo_name=repo_name)

        # Step 4: Insert findings into database (without explanations)
        for finding in findings:
            finding_dict = finding.to_dict()
            db.insert_finding(run_id, finding_dict)

        # Step 5: Mark run as complete
        db.complete_analysis_run(run_id, len(findings))

        # Save findings.json for reference
        with open(project_root / "DATA" / "outputs" / "findings.json", "w") as f:
            json_module.dump([f.to_dict() for f in findings], f, indent=2)

        # Category breakdown
        from collections import Counter

        cats = Counter(f.category for f in findings)

        return jsonify(
            {
                "success": True,
                "run_id": run_id,
                "total_findings": len(findings),
                "categories": dict(cats),
                "message": f"Quick refresh complete! {len(findings)} findings stored in database.",
                "note": "No AI explanations generated (use main.py for full analysis)",
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/health")
def health_check():
    """Health check endpoint for cloud deployment"""
    from CORE import __version__

    return jsonify({"status": "healthy", "version": __version__})


@app.route("/api/analyze", methods=["POST"])
def analyze_single_file():
    """
    Analyze a single file and return findings
    Used by VSCode extension for real-time analysis
    """
    import json as json_module
    import subprocess
    import tempfile

    try:
        data = request.get_json()
        content = data.get("content", "")
        filename = data.get("filename", "temp.py")

        if not content:
            return jsonify({"success": False, "error": "No content provided"}), 400

        # Create temp file with content
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(content)
            temp_path = f.name

        findings = []

        try:
            # Run Ruff (fast linter)
            result = subprocess.run(
                ["ruff", "check", temp_path, "--output-format=json"],
                capture_output=True,
                text=True,
            )
            if result.stdout:
                ruff_findings = json_module.loads(result.stdout)
                for finding in ruff_findings:
                    findings.append(
                        {
                            "line": finding.get("location", {}).get("row", 1),
                            "column": finding.get("location", {}).get("column", 1),
                            "rule_id": finding.get("code", "UNKNOWN"),
                            "severity": "medium" if finding.get("code", "").startswith("E") else "low",
                            "message": finding.get("message", ""),
                            "tool": "ruff",
                        }
                    )

            # Run Vulture (unused code detection)
            result = subprocess.run(
                ["vulture", temp_path, "--min-confidence", "80"],
                capture_output=True,
                text=True,
            )
            for line in result.stdout.strip().split("\n"):
                if line and ":" in line:
                    parts = line.split(":")
                    if len(parts) >= 3:
                        findings.append(
                            {
                                "line": int(parts[1]) if parts[1].isdigit() else 1,
                                "column": 1,
                                "rule_id": "DEAD-001",
                                "severity": "low",
                                "message": ":".join(parts[2:]).strip(),
                                "tool": "vulture",
                            }
                        )

            # Run Bandit (security scanner)
            try:
                result = subprocess.run(
                    ["bandit", "-f", "json", "-q", temp_path],
                    capture_output=True,
                    text=True,
                )
                if result.stdout:
                    bandit_data = json_module.loads(result.stdout)
                    for issue in bandit_data.get("results", []):
                        sev = issue.get("issue_severity", "LOW").lower()
                        findings.append(
                            {
                                "line": issue.get("line_number", 1),
                                "column": 1,
                                "rule_id": issue.get("test_id", "B000"),
                                "severity": "high" if sev == "high" else "medium" if sev == "medium" else "low",
                                "message": issue.get("issue_text", ""),
                                "tool": "bandit",
                                "category": "security",
                            }
                        )
            except Exception:
                pass  # Bandit not installed or failed — skip

        finally:
            # Clean up temp file
            os.unlink(temp_path)

        return jsonify(
            {
                "success": True,
                "filename": filename,
                "findings": findings,
                "total": len(findings),
            }
        )

    except Exception as e:
        logger.error(f"Error in /api/analyze: {e}")

        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/quick-stats")
def quick_stats():
    """
    Quick stats endpoint for dashboards and integrations
    Returns summary statistics for recent runs
    """
    try:
        runs = db.get_recent_runs(limit=10)

        total_findings = 0
        total_high = 0
        total_medium = 0
        total_low = 0

        for run in runs:
            summary = db.get_run_summary(run["id"])
            if summary:
                total_findings += summary.get("findings_count", 0)
                total_high += summary.get("high_severity_count", 0)
                total_medium += summary.get("medium_severity_count", 0)
                total_low += summary.get("low_severity_count", 0)

        return jsonify(
            {
                "success": True,
                "stats": {
                    "total_runs": len(runs),
                    "total_findings": total_findings,
                    "high_severity": total_high,
                    "medium_severity": total_medium,
                    "low_severity": total_low,
                    "avg_findings_per_run": round(total_findings / len(runs), 1) if runs else 0,
                },
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/runs/<int:run_id>/summary")
def get_pr_summary(run_id):
    """
    Generate PR-style summary for a run
    Used by GitHub/GitLab integrations
    """
    try:
        from collections import Counter

        runs = db.get_recent_runs(limit=100)
        run = next((r for r in runs if r["id"] == run_id), None)

        if not run:
            return jsonify({"success": False, "error": "Run not found"}), 404

        findings = db.get_findings(run_id)

        # Calculate stats
        severity_counts = Counter(f.get("severity", "low") for f in findings)
        category_counts = Counter(f.get("category", "unknown") for f in findings)

        # Critical findings
        critical = [f for f in findings if f.get("severity") in ("high", "critical")]

        summary_md = f"""## 📊 ACR-QA Analysis Summary

**Total Issues:** {len(findings)}
**Critical/High:** {severity_counts.get('high', 0) + severity_counts.get('critical', 0)}
**Medium:** {severity_counts.get('medium', 0)}
**Low:** {severity_counts.get('low', 0)}

### Top Categories
"""
        for cat, count in category_counts.most_common(3):
            summary_md += f"- **{cat}**: {count}\n"

        if critical:
            summary_md += f"\n### 🚨 Critical Issues ({len(critical)})\n"
            for f in critical[:3]:
                summary_md += f"- {f.get('canonical_rule_id', 'UNKNOWN')}: {f.get('message', '')[:60]}\n"

        return jsonify(
            {
                "success": True,
                "run_id": run_id,
                "summary_markdown": summary_md,
                "stats": {
                    "total": len(findings),
                    "high": severity_counts.get("high", 0) + severity_counts.get("critical", 0),
                    "medium": severity_counts.get("medium", 0),
                    "low": severity_counts.get("low", 0),
                },
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/fix-confidence/<rule_id>")
def get_fix_confidence(rule_id):
    """
    Get confidence score for auto-fix capability
    Returns how confident the system is in auto-fixing this rule
    """
    # High confidence rules (well-tested fixes)
    high_confidence = {
        "IMPORT-001": 95,  # Remove unused import
        "VAR-001": 90,  # Prefix with underscore
        "BOOL-001": 95,  # Simplify boolean
        "F401": 95,  # Ruff unused import
        "F841": 85,  # Ruff unused variable
    }

    # Medium confidence (usually works)
    medium_confidence = {
        "PATTERN-001": 75,  # Mutable default
        "STYLE-001": 80,  # Line too long
        "E501": 80,  # Ruff line length
    }

    # Low confidence (needs review)
    low_confidence = {
        "SECURITY-001": 40,  # eval() - needs context
        "COMPLEXITY-001": 30,  # Refactoring needed
        "DUP-001": 25,  # Duplication - needs judgment
    }

    confidence = high_confidence.get(rule_id) or medium_confidence.get(rule_id) or low_confidence.get(rule_id) or 50

    level = "high" if confidence >= 80 else "medium" if confidence >= 60 else "low"

    return jsonify(
        {
            "success": True,
            "rule_id": rule_id,
            "confidence": confidence,
            "level": level,
            "auto_fixable": confidence >= 70,
            "recommendation": "Safe to auto-apply"
            if confidence >= 80
            else "Review recommended"
            if confidence >= 60
            else "Manual fix recommended",
        }
    )


@app.route("/api/trends")
def get_trends():
    """
    Get trend analytics data for dashboard visualization.
    Returns time-series severity, category, and confidence data across recent runs.
    Query params:
        limit (int): number of runs to include (default 30)
        repo (str): filter by repo name (optional)
    """
    try:
        limit = request.args.get("limit", 30, type=int)
        repo = request.args.get("repo", None)
        trend_data = db.get_trend_data(limit=limit, repo_name=repo)
        repos = db.get_repos_with_runs()

        labels = []
        severity_series = {"high": [], "medium": [], "low": []}
        category_series = {"security": [], "style": [], "design": [], "best_practice": []}
        confidence_series = []
        total_series = []
        run_ids = []

        for row in reversed(trend_data):  # Chronological order
            started = row.get("started_at")
            label = str(started)[:10] if started else "unknown"
            labels.append(f"{label} ({row.get('repo_name', '?')})")
            run_ids.append(row.get("run_id"))

            severity_series["high"].append(int(row.get("high_count", 0)))
            severity_series["medium"].append(int(row.get("medium_count", 0)))
            severity_series["low"].append(int(row.get("low_count", 0)))

            category_series["security"].append(int(row.get("security_count", 0)))
            category_series["style"].append(int(row.get("style_count", 0)))
            category_series["design"].append(int(row.get("design_count", 0)))
            category_series["best_practice"].append(int(row.get("best_practice_count", 0)))

            confidence_series.append(round(float(row.get("avg_confidence", 0)), 1))
            total_series.append(int(row.get("total_findings", 0)))

        return jsonify(
            {
                "success": True,
                "labels": labels,
                "run_ids": run_ids,
                "repos": repos,
                "severity_series": severity_series,
                "category_series": category_series,
                "confidence_series": confidence_series,
                "total_series": total_series,
                "run_count": len(trend_data),
            }
        )

    except Exception as e:
        logger.error(f"Error in /api/trends: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/repos")
def get_repos():
    """Get list of repos that have completed analysis runs."""
    try:
        repos = db.get_repos_with_runs()
        return jsonify({"success": True, "repos": repos})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/runs/<int:run_id>/compliance")
def get_compliance_report(run_id):
    """
    OWASP Top 10 compliance report for an analysis run.
    Maps security findings to OWASP categories and CWE IDs.
    Returns JSON with pass/fail per category.
    """
    try:
        from scripts.generate_compliance_report import get_compliance_data

        data = get_compliance_data(run_id=run_id)
        if isinstance(data, str):
            return jsonify({"success": False, "error": data}), 404

        return jsonify({"success": True, **data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/test-gaps")
def get_test_gaps():
    """
    Test gap analysis — find untested functions/classes.
    No competitor does this. Market differentiator.
    """
    try:
        from scripts.test_gap_analyzer import get_test_gap_data

        target = request.args.get("target", "CORE/")
        test_dir = request.args.get("test_dir", "TESTS/")

        data = get_test_gap_data(target_dir=target, test_dir=test_dir)
        return jsonify({"success": True, **data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/policy")
def get_policy_config():
    """
    Returns the active policy configuration from .acrqa.yml.
    Shows what rules are enforced, quality gates, severity overrides, etc.
    This IS the policy-as-code engine — the config file defines the policy.
    """
    try:
        from scripts.validate_config import SCHEMA, validate_config

        config_path = ".acrqa.yml"
        is_valid, errors, warnings = validate_config(config_path)

        # Read active config
        import yaml

        config = {}
        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file) as f:
                config = yaml.safe_load(f) or {}

        # Build policy summary
        policy = {
            "config_file": config_path,
            "is_valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "active_policy": {
                "disabled_rules": config.get("rules", {}).get("disabled_rules", []),
                "severity_overrides": config.get("rules", {}).get("severity_overrides", {}),
                "ignored_paths": config.get("analysis", {}).get("ignore_paths", []),
                "min_severity": config.get("reporting", {}).get("min_severity", "low"),
                "quality_gate": config.get(
                    "quality_gate",
                    {
                        "max_high": 0,
                        "max_medium": 10,
                        "max_total": 200,
                        "max_security": 0,
                    },
                ),
                "autofix": {
                    "enabled": config.get("autofix", {}).get("enabled", False),
                    "min_confidence": config.get("autofix", {}).get("auto_apply_confidence", 80),
                },
                "ai_explanations": {
                    "enabled": config.get("ai", {}).get("enabled", True),
                    "max_explanations": config.get("ai", {}).get("max_explanations", 50),
                },
            },
            "schema_keys": list(SCHEMA.keys()),
        }

        return jsonify({"success": True, **policy})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/scan/secrets", methods=["POST"])
def scan_secrets():
    """Run secrets detection on a target directory."""
    try:
        data = request.get_json() or {}
        target_dir = data.get("target_dir", ".")

        from CORE.engines.secrets_detector import SecretsDetector

        detector = SecretsDetector()
        results = detector.scan_directory(target_dir)

        return jsonify(
            {
                "success": True,
                "files_scanned": results["files_scanned"],
                "total_secrets": results["total_secrets"],
                "severity_breakdown": results["severity_breakdown"],
                "secret_types": results["secret_types_found"],
                "findings": results["findings"][:50],  # Limit response size
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/scan/sca", methods=["POST"])
def scan_dependencies():
    """Run SCA (dependency vulnerability) scan."""
    try:
        data = request.get_json() or {}
        project_dir = data.get("project_dir", ".")

        from CORE.engines.sca_scanner import SCAScanner

        scanner = SCAScanner(project_dir=project_dir)
        results = scanner.scan()

        return jsonify(
            {
                "success": True,
                "scanner": results["scanner"],
                "total_vulnerabilities": results["total_vulnerabilities"],
                "severity_breakdown": results["severity_breakdown"],
                "vulnerabilities": results["vulnerabilities"],
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/scan/ai-detection", methods=["POST"])
def scan_ai_code():
    """Run AI-generated code detection on a target."""
    try:
        data = request.get_json() or {}
        target = data.get("target", ".")
        threshold = data.get("threshold", 0.5)

        from CORE.engines.ai_code_detector import AICodeDetector

        detector = AICodeDetector(threshold=threshold)

        if Path(target).is_file():
            result = detector.analyze_file(target)
            return jsonify({"success": True, "result": result})
        else:
            results = detector.analyze_directory(target)
            return jsonify(
                {
                    "success": True,
                    "total_files": results["total_files"],
                    "flagged_files": results["flagged_files"],
                    "flagged_percentage": results["flagged_percentage"],
                    "files": results["files"][:50],  # Limit response size
                }
            )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/cost-benefit/<int:run_id>")
@track_request("/api/cost-benefit")
def cost_benefit(run_id):
    """N4: Cost-benefit analysis for an analysis run."""
    try:
        findings = db.get_findings(run_id)
        if not findings:
            return jsonify({"success": False, "error": "No findings found"})

        # Calculate total LLM cost from explanations
        total_cost = 0.0
        for f in findings:
            cost = f.get("cost_usd", 0) or 0
            total_cost += float(cost)

        # Estimate hours saved:
        # High severity: ~30 min manual review each
        # Medium: ~15 min, Low: ~5 min
        hours_saved = 0
        for f in findings:
            sev = (f.get("severity", "low") or "low").lower()
            if sev == "high":
                hours_saved += 0.5
            elif sev == "medium":
                hours_saved += 0.25
            else:
                hours_saved += 0.083  # ~5 min

        # Developer cost: ~$75/hr average
        dev_cost_saved = hours_saved * 75
        roi = dev_cost_saved / total_cost if total_cost > 0 else float("inf")
        cost_per_finding = total_cost / len(findings) if findings else 0

        return jsonify(
            {
                "success": True,
                "analysis_cost_usd": round(total_cost, 4),
                "hours_saved": round(hours_saved, 1),
                "dev_cost_saved_usd": round(dev_cost_saved, 2),
                "roi_ratio": round(roi, 0) if roi != float("inf") else "∞",
                "cost_per_finding": round(cost_per_finding, 5),
                "total_findings": len(findings),
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/findings/<int:finding_id>/mark-false-positive", methods=["POST"])
@track_request("/api/findings/mark-false-positive")
def mark_false_positive(finding_id):
    """Mark a finding as a false positive via user feedback."""
    try:
        # Check if finding exists before inserting feedback
        existing = db.execute("SELECT id FROM findings WHERE id = %s", (finding_id,), fetch=True)
        if not existing:
            return jsonify({"success": False, "error": f"Finding {finding_id} not found"}), 404

        data = request.get_json() or {}
        reason = data.get("reason", "")
        user_id = data.get("user_id", "dashboard-user")

        feedback_id = db.insert_feedback(
            finding_id=finding_id,
            user_id=user_id,
            is_false_positive=True,
            is_helpful=False,
            comment=reason,
        )

        if feedback_id:
            # Feature 6 — Triage Memory: learn suppression rule from this FP
            try:
                from CORE.engines.triage_memory import TriageMemory

                TriageMemory().learn_from_fp(finding_id, db)
            except Exception as _tm_err:
                app.logger.warning("TriageMemory.learn_from_fp failed: %s", _tm_err)

            return jsonify(
                {
                    "success": True,
                    "feedback_id": feedback_id,
                    "message": f"Finding {finding_id} marked as false positive — suppression rule created",
                }
            )
        else:
            return jsonify({"success": False, "error": "Failed to store feedback"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/suppression-rules", methods=["GET"])
@track_request("/api/suppression-rules")
def get_suppression_rules():
    """Return all active suppression rules learned from FP feedback (Feature 6)."""
    try:
        rules = db.get_suppression_rules(active_only=True)
        # Convert datetime to string for JSON serialisation
        for r in rules:
            if r.get("created_at"):
                r["created_at"] = r["created_at"].isoformat()
        return jsonify({"rules": rules, "count": len(rules)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/findings/<int:finding_id>/feedback", methods=["POST"])
@track_request("/api/findings/feedback")
def submit_feedback(finding_id):
    """Submit general feedback (helpful/not helpful) for a finding."""
    try:
        # Check if finding exists before inserting feedback
        existing = db.execute("SELECT id FROM findings WHERE id = %s", (finding_id,), fetch=True)
        if not existing:
            return jsonify({"success": False, "error": f"Finding {finding_id} not found"}), 404

        data = request.get_json() or {}
        is_helpful = data.get("is_helpful", True)
        clarity_rating = data.get("clarity_rating")
        comment = data.get("comment", "")
        user_id = data.get("user_id", "dashboard-user")

        feedback_id = db.insert_feedback(
            finding_id=finding_id,
            user_id=user_id,
            is_false_positive=False,
            is_helpful=is_helpful,
            clarity_rating=clarity_rating,
            comment=comment,
        )

        if feedback_id:
            return jsonify({"success": True, "feedback_id": feedback_id})
        else:
            return jsonify({"success": False, "error": "Failed to store feedback"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    logger.info("🚀 Starting ACR-QA Dashboard...")
    logger.info("📊 Access at: http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
