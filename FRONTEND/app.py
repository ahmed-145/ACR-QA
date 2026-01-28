#!/usr/bin/env python3
"""
ACR-QA v2.0 Web Dashboard
Flask + Tailwind CSS
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from DATABASE.database import Database

app = Flask(__name__)
CORS(app)
# Security: Use environment variable for SECRET_KEY
app.config["SECRET_KEY"] = os.getenv(
    "FLASK_SECRET_KEY", "dev-secret-key-change-in-production"
)

db = Database()


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
                    "total_findings": summary.get("findings_count", 0)
                    if summary
                    else 0,
                    "high_count": summary.get("high_severity_count", 0)
                    if summary
                    else 0,
                    "medium_count": summary.get("medium_severity_count", 0)
                    if summary
                    else 0,
                    "low_count": summary.get("low_severity_count", 0) if summary else 0,
                }
            )

        return jsonify({"success": True, "runs": runs_with_summary})
    except Exception as e:
        print(f"Error in /api/runs: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/runs/<int:run_id>/findings")
def get_run_findings(run_id):
    """Get findings for a specific run with filters"""
    try:
        severity = request.args.get('severity')
        category = request.args.get('category')
        search = request.args.get('search', '').lower()
        group_by = request.args.get('group_by')  # New: 'rule' for grouping
        
        # Get findings
        findings = db.get_findings_with_explanations(run_id)
        
        # Apply filters
        filtered = []
        for f in findings:
            # Severity filter
            if severity and f.get('canonical_severity') != severity:
                continue
            
            # Category filter
            if category and f.get('category') != category:
                continue
            
            # Search filter
            if search:
                searchable = f"{f.get('file_path', '')} {f.get('message', '')} {f.get('canonical_rule_id', '')}".lower()
                if search not in searchable:
                    continue
            
            filtered.append({
                'id': f['id'],
                'rule_id': f.get('canonical_rule_id', f.get('rule_id')),
                'severity': f.get('canonical_severity', 'low'),
                'category': f.get('category'),
                'file_path': f.get('file_path'),
                'line_number': f.get('line_number'),
                'message': f.get('message'),
                'explanation_text': f.get('explanation_text'),
                'model_name': f.get('model_name'),
                'latency_ms': f.get('latency_ms'),
                'tool': f.get('tool'),
                # LOW Priority: Display confidence score (calculated based on rule citation)
                'confidence': 0.9 if f.get('explanation_text') and f.get('canonical_rule_id', '') in str(f.get('explanation_text', '')) else 0.6,
                'ground_truth': f.get('ground_truth')  # For Phase 2 evaluation
            })
        
        # Polish: Group by rule if requested
        if group_by == 'rule':
            grouped = {}
            for f in filtered:
                rule_id = f['rule_id']
                if rule_id not in grouped:
                    grouped[rule_id] = {
                        'rule_id': rule_id,
                        'count': 0,
                        'severity': f['severity'],
                        'category': f['category'],
                        'findings': []
                    }
                grouped[rule_id]['count'] += 1
                grouped[rule_id]['findings'].append(f)
            
            return jsonify({
                'success': True,
                'grouped': True,
                'groups': list(grouped.values()),
                'total': len(filtered)
            })
        
        return jsonify({
            'success': True,
            'findings': filtered,
            'total': len(filtered)
        })
    except Exception as e:
        print(f"Error in /api/runs/{run_id}/findings: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


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
        print(f"Error in /api/runs/{run_id}/stats: {e}")
        import traceback

        traceback.print_exc()
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
        print(f"Error in /api/categories: {e}")
        return jsonify({"success": False, "error": str(e)}), 500



@app.route("/api/refresh-findings", methods=["POST"])
def refresh_findings():
    """
    Quick Refresh: Re-run detection tools and update database
    WITHOUT generating AI explanations (fast refresh for development)
    
    This solves the synchronization issue where tool outputs are updated
    but the database still has old data.
    """
    import subprocess
    import json as json_module
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
                capture_output=True
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
        
        return jsonify({
            "success": True,
            "run_id": run_id,
            "total_findings": len(findings),
            "categories": dict(cats),
            "message": f"Quick refresh complete! {len(findings)} findings stored in database.",
            "note": "No AI explanations generated (use main.py for full analysis)"
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/health")
def health_check():
    """Health check endpoint for cloud deployment"""
    return jsonify({"status": "healthy", "version": "2.0"})



@app.route("/api/analyze", methods=["POST"])
def analyze_single_file():
    """
    Analyze a single file and return findings
    Used by VSCode extension for real-time analysis
    """
    import tempfile
    import subprocess
    import json as json_module
    
    try:
        data = request.get_json()
        content = data.get("content", "")
        filename = data.get("filename", "temp.py")
        
        if not content:
            return jsonify({"success": False, "error": "No content provided"}), 400
        
        # Create temp file with content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        findings = []
        
        try:
            # Run Ruff (fast linter)
            result = subprocess.run(
                ["ruff", "check", temp_path, "--output-format=json"],
                capture_output=True, text=True
            )
            if result.stdout:
                ruff_findings = json_module.loads(result.stdout)
                for finding in ruff_findings:
                    findings.append({
                        "line": finding.get("location", {}).get("row", 1),
                        "column": finding.get("location", {}).get("column", 1),
                        "rule_id": finding.get("code", "UNKNOWN"),
                        "severity": "medium" if finding.get("code", "").startswith("E") else "low",
                        "message": finding.get("message", ""),
                        "tool": "ruff"
                    })
            
            # Run Vulture (unused code detection)
            result = subprocess.run(
                ["vulture", temp_path, "--min-confidence", "80"],
                capture_output=True, text=True
            )
            for line in result.stdout.strip().split('\n'):
                if line and ':' in line:
                    parts = line.split(':')
                    if len(parts) >= 3:
                        findings.append({
                            "line": int(parts[1]) if parts[1].isdigit() else 1,
                            "column": 1,
                            "rule_id": "DEAD-001",
                            "severity": "low",
                            "message": ':'.join(parts[2:]).strip(),
                            "tool": "vulture"
                        })
            
        finally:
            # Clean up temp file
            os.unlink(temp_path)
        
        return jsonify({
            "success": True,
            "filename": filename,
            "findings": findings,
            "total": len(findings)
        })
        
    except Exception as e:
        print(f"Error in /api/analyze: {e}")
        import traceback
        traceback.print_exc()
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
        
        return jsonify({
            "success": True,
            "stats": {
                "total_runs": len(runs),
                "total_findings": total_findings,
                "high_severity": total_high,
                "medium_severity": total_medium,
                "low_severity": total_low,
                "avg_findings_per_run": round(total_findings / len(runs), 1) if runs else 0
            }
        })
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
        run = next((r for r in runs if r['id'] == run_id), None)
        
        if not run:
            return jsonify({"success": False, "error": "Run not found"}), 404
        
        findings = db.get_findings(run_id)
        
        # Calculate stats
        severity_counts = Counter(f.get('severity', 'low') for f in findings)
        category_counts = Counter(f.get('category', 'unknown') for f in findings)
        
        # Critical findings
        critical = [f for f in findings if f.get('severity') in ('high', 'critical')]
        
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
        
        return jsonify({
            "success": True,
            "run_id": run_id,
            "summary_markdown": summary_md,
            "stats": {
                "total": len(findings),
                "high": severity_counts.get('high', 0) + severity_counts.get('critical', 0),
                "medium": severity_counts.get('medium', 0),
                "low": severity_counts.get('low', 0)
            }
        })
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
        "VAR-001": 90,     # Prefix with underscore
        "BOOL-001": 95,    # Simplify boolean
        "F401": 95,        # Ruff unused import
        "F841": 85,        # Ruff unused variable
    }
    
    # Medium confidence (usually works)
    medium_confidence = {
        "PATTERN-001": 75,  # Mutable default
        "STYLE-001": 80,    # Line too long
        "E501": 80,         # Ruff line length
    }
    
    # Low confidence (needs review)
    low_confidence = {
        "SECURITY-001": 40,  # eval() - needs context
        "COMPLEXITY-001": 30,  # Refactoring needed
        "DUP-001": 25,  # Duplication - needs judgment
    }
    
    confidence = high_confidence.get(rule_id) or \
                 medium_confidence.get(rule_id) or \
                 low_confidence.get(rule_id) or 50
    
    level = "high" if confidence >= 80 else "medium" if confidence >= 60 else "low"
    
    return jsonify({
        "success": True,
        "rule_id": rule_id,
        "confidence": confidence,
        "level": level,
        "auto_fixable": confidence >= 70,
        "recommendation": "Safe to auto-apply" if confidence >= 80 else 
                         "Review recommended" if confidence >= 60 else
                         "Manual fix recommended"
    })


if __name__ == "__main__":
    print("🚀 Starting ACR-QA Dashboard...")
    print("📊 Access at: http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)

