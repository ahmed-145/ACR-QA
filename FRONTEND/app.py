#!/usr/bin/env python3
"""
ACR-QA v2.0 Web Dashboard
Flask + Bootstrap 5 + Chart.js
"""
from flask import Flask, render_template, jsonify, request, send_file
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from DATABASE.database import Database

import json
from datetime import datetime
from pathlib import Path

app = Flask(__name__)
app.config['SECRET_KEY'] = 'acr-qa-v2-secret-key-change-in-production'

# Initialize database
db = Database()


@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')


@app.route('/api/runs')
def get_runs():
    """Get all analysis runs"""
    try:
        runs = db.get_recent_runs(limit=50)
        
        # Convert datetime to string for JSON serialization
        for run in runs:
            run['started_at'] = str(run['started_at']) if run['started_at'] else None
            run['completed_at'] = str(run['completed_at']) if run['completed_at'] else None
        
        return jsonify({'success': True, 'runs': runs})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/run/<int:run_id>')
def get_run_details(run_id):
    """Get detailed information about a specific run"""
    try:
        run_info = db.get_run_info(run_id)
        if not run_info:
            return jsonify({'success': False, 'error': 'Run not found'}), 404
        
        # Get findings with explanations
        findings = db.get_findings_with_explanations(run_id)
        
        # Convert datetime to string
        run_info['started_at'] = str(run_info['started_at']) if run_info['started_at'] else None
        run_info['completed_at'] = str(run_info['completed_at']) if run_info['completed_at'] else None
        
        # Calculate statistics
        stats = {
            'total_findings': len(findings),
            'by_severity': {},
            'by_category': {},
            'by_tool': {},
            'with_explanations': sum(1 for f in findings if f.get('explanation_text')),
            'avg_latency': 0
        }
        
        latencies = []
        for f in findings:
            # Count by severity
            sev = f['severity']
            stats['by_severity'][sev] = stats['by_severity'].get(sev, 0) + 1
            
            # Count by category
            cat = f['category']
            stats['by_category'][cat] = stats['by_category'].get(cat, 0) + 1
            
            # Count by tool
            tool = f['tool']
            stats['by_tool'][tool] = stats['by_tool'].get(tool, 0) + 1
            
            # Latency
            if f.get('latency_ms'):
                latencies.append(f['latency_ms'])
        
        if latencies:
            stats['avg_latency'] = int(sum(latencies) / len(latencies))
        
        return jsonify({
            'success': True,
            'run': run_info,
            'findings': findings,
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/finding/<int:finding_id>/feedback', methods=['POST'])
def submit_feedback(finding_id):
    """Submit feedback for a finding"""
    try:
        data = request.json
        
        feedback_id = db.insert_feedback(
            finding_id=finding_id,
            user_id=data.get('user_id', 'anonymous'),
            is_false_positive=data.get('is_false_positive'),
            is_helpful=data.get('is_helpful'),
            clarity_rating=data.get('clarity_rating'),
            comment=data.get('comment')
        )
        
        return jsonify({'success': True, 'feedback_id': feedback_id})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/stats')
def get_stats():
    """Get overall statistics"""
    try:
        feedback_stats = db.get_feedback_stats()
        runs = db.get_recent_runs(limit=100)
        
        total_runs = len(runs)
        completed_runs = sum(1 for r in runs if r['status'] == 'completed')
        total_findings = sum(r['total_findings'] or 0 for r in runs)
        
        return jsonify({
            'success': True,
            'stats': {
                'total_runs': total_runs,
                'completed_runs': completed_runs,
                'total_findings': total_findings,
                'feedback': feedback_stats
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/export/<int:run_id>')
def export_run(run_id):
    """Export run data as JSON"""
    try:
        run_info = db.get_run_info(run_id)
        findings = db.get_findings_with_explanations(run_id)
        
        # Convert to serializable format
        run_info['started_at'] = str(run_info['started_at'])
        run_info['completed_at'] = str(run_info['completed_at']) if run_info['completed_at'] else None
        
        export_data = {
            'run': run_info,
            'findings': findings,
            'exported_at': datetime.now().isoformat()
        }
        
        # Save to file
        export_path = Path('outputs') / f'export_run_{run_id}.json'
        export_path.parent.mkdir(exist_ok=True)
        
        with open(export_path, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        return send_file(export_path, as_attachment=True)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    print("🚀 ACR-QA v2.0 Web Dashboard Starting...")
    print("📊 Access at: http://localhost:5000")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)