#!/usr/bin/env python3
"""
ACR-QA v2.0 Web Dashboard
Flask + Tailwind CSS
"""
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from DATABASE.database import Database

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = 'acr-qa-v2-secret-key'

db = Database()


@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')


@app.route('/api/runs')
def get_runs():
    """Get recent analysis runs"""
    try:
        limit = request.args.get('limit', 10, type=int)
        runs = db.get_recent_runs(limit=limit)
        
        # Add summary for each run
        runs_with_summary = []
        for run in runs:
            summary = db.get_run_summary(run['id'])
            runs_with_summary.append({
                'id': run['id'],
                'repo_name': run['repo_name'],
                'pr_number': run.get('pr_number'),
                'status': run['status'],
                'started_at': str(run['started_at']),
                'total_findings': summary.get('findings_count', 0) if summary else 0,
                'high_count': summary.get('high_severity_count', 0) if summary else 0,
                'medium_count': summary.get('medium_severity_count', 0) if summary else 0,
                'low_count': summary.get('low_severity_count', 0) if summary else 0
            })
        
        return jsonify({'success': True, 'runs': runs_with_summary})
    except Exception as e:
        print(f"Error in /api/runs: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/runs/<int:run_id>/findings')
def get_run_findings(run_id):
    """Get findings for a specific run with filters"""
    try:
        severity = request.args.get('severity')
        category = request.args.get('category')
        search = request.args.get('search', '').lower()
        
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
                'tool': f.get('tool')
            })
        
        return jsonify({
            'success': True,
            'total': len(filtered),
            'findings': filtered
        })
    except Exception as e:
        print(f"Error in /api/runs/{run_id}/findings: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/runs/<int:run_id>/stats')
def get_run_stats(run_id):
    """Get statistics for a run"""
    try:
        summary = db.get_run_summary(run_id)
        
        if not summary:
            return jsonify({'success': False, 'error': 'Run not found'}), 404
        
        return jsonify({
            'success': True,
            'run_id': run_id,
            'repo_name': summary.get('repo_name'),
            'status': summary.get('status'),
            'total_findings': summary.get('findings_count', 0),
            'high': summary.get('high_severity_count', 0),
            'medium': summary.get('medium_severity_count', 0),
            'low': summary.get('low_severity_count', 0),
            'explanations_count': summary.get('explanations_count', 0),
            'avg_latency_ms': float(summary.get('avg_explanation_latency', 0) or 0),
            'total_cost_usd': float(summary.get('total_cost', 0) or 0)
        })
    except Exception as e:
        print(f"Error in /api/runs/{run_id}/stats: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/categories')
def get_categories():
    """Get all available categories"""
    try:
        runs = db.get_recent_runs(limit=1)
        if not runs:
            return jsonify({'success': True, 'categories': []})
        
        findings = db.get_findings(run_id=runs[0]['id'], limit=1000)
        categories = sorted(set(f['category'] for f in findings))
        
        return jsonify({'success': True, 'categories': categories})
    except Exception as e:
        print(f"Error in /api/categories: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    print("🚀 Starting ACR-QA Dashboard...")
    print("📊 Access at: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)