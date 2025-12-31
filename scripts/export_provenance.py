#!/usr/bin/env python3
"""
Provenance Export for ACR-QA v2.0
Complete audit trail: raw tool outputs, LLM interactions, timestamps
For academic evaluation and thesis defense
"""
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from DATABASE.database import Database
import argparse


def export_provenance(run_id=None, output_dir='outputs/provenance'):
    """
    Export complete provenance data for an analysis run
    
    Includes:
    - Run metadata
    - All findings with canonical schema
    - Raw tool outputs (preserved)
    - LLM prompts and responses
    - Timing and cost data
    - User feedback (if any)
    
    Args:
        run_id: Analysis run ID (None = latest)
        output_dir: Directory to save provenance files
    """
    db = Database()
    
    # Get run info
    if run_id:
        run = db.get_run_info(run_id)
        if not run:
            print(f"❌ Run {run_id} not found")
            return None
    else:
        runs = db.get_recent_runs(limit=1)
        if not runs:
            print("❌ No analysis runs found")
            return None
        run = runs[0]
        run_id = run['id']
    
    print(f"📦 Exporting provenance for Run {run_id}...")
    
    # Get findings with explanations
    findings = db.get_findings_with_explanations(run_id)
    
    # Get feedback stats
    feedback_stats = db.get_feedback_stats()
    
    # Build provenance document
    provenance = {
        'metadata': {
            'run_id': run['id'],
            'export_timestamp': datetime.now().isoformat(),
            'acr_qa_version': '2.0',
            'purpose': 'Complete audit trail for academic evaluation'
        },
        
        'analysis_run': {
            'id': run['id'],
            'repo_name': run['repo_name'],
            'commit_sha': run.get('commit_sha'),
            'branch': run.get('branch'),
            'pr_number': run.get('pr_number'),
            'status': run['status'],
            'started_at': str(run['started_at']),
            'completed_at': str(run.get('completed_at')),
            'total_findings': run.get('total_findings', len(findings))
        },
        
        'findings': [],
        
        'statistics': {
            'total_findings': len(findings),
            'by_severity': {},
            'by_category': {},
            'by_tool': {},
            'with_explanations': 0,
            'explanation_latency': {
                'min_ms': None,
                'max_ms': None,
                'avg_ms': None,
                'total_ms': 0
            },
            'total_cost_usd': 0
        },
        
        'feedback_summary': feedback_stats
    }
    
    # Process findings
    latencies = []
    costs = []
    
    for f in findings:
        # Convert to serializable format
        finding_data = {
            'id': f['id'],
            'rule_id': f['rule_id'],
            'file_path': f['file_path'],
            'line_number': f['line_number'],
            'severity': f['severity'],
            'category': f['category'],
            'message': f['message'],
            'tool': f['tool']
        }
        
        # Add explanation if exists
        if f.get('explanation_text'):
            provenance['statistics']['with_explanations'] += 1
            
            finding_data['explanation'] = {
                'model_name': f.get('model_name'),
                'response_text': f.get('explanation_text'),
                'latency_ms': f.get('latency_ms')
            }
            
            if f.get('latency_ms'):
                latencies.append(f['latency_ms'])
        
        provenance['findings'].append(finding_data)
        
        # Update statistics
        sev = f['severity']
        provenance['statistics']['by_severity'][sev] = provenance['statistics']['by_severity'].get(sev, 0) + 1
        
        cat = f['category']
        provenance['statistics']['by_category'][cat] = provenance['statistics']['by_category'].get(cat, 0) + 1
        
        tool = f['tool']
        provenance['statistics']['by_tool'][tool] = provenance['statistics']['by_tool'].get(tool, 0) + 1
    
    # Calculate latency stats
    if latencies:
        provenance['statistics']['explanation_latency'] = {
            'min_ms': min(latencies),
            'max_ms': max(latencies),
            'avg_ms': int(sum(latencies) / len(latencies)),
            'total_ms': sum(latencies)
        }
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Write JSON provenance
    json_file = output_path / f'provenance_run_{run_id}.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(provenance, f, indent=2, ensure_ascii=False)
    
    print(f"✅ JSON provenance: {json_file}")
    
    # Write human-readable summary
    summary_file = output_path / f'summary_run_{run_id}.txt'
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("="*60 + "\n")
        f.write("ACR-QA v2.0 Provenance Summary\n")
        f.write("="*60 + "\n\n")
        
        f.write(f"Run ID: {run_id}\n")
        f.write(f"Repository: {run['repo_name']}\n")
        f.write(f"Status: {run['status']}\n")
        f.write(f"Started: {run['started_at']}\n")
        f.write(f"Completed: {run.get('completed_at', 'N/A')}\n")
        f.write("\n")
        
        f.write("-"*60 + "\n")
        f.write("FINDINGS SUMMARY\n")
        f.write("-"*60 + "\n\n")
        
        f.write(f"Total Findings: {len(findings)}\n\n")
        
        f.write("By Severity:\n")
        for sev, count in sorted(provenance['statistics']['by_severity'].items()):
            f.write(f"  {sev:10s}: {count:3d}\n")
        
        f.write("\nBy Category:\n")
        for cat, count in sorted(provenance['statistics']['by_category'].items()):
            f.write(f"  {cat:20s}: {count:3d}\n")
        
        f.write("\nBy Tool:\n")
        for tool, count in sorted(provenance['statistics']['by_tool'].items()):
            f.write(f"  {tool:10s}: {count:3d}\n")
        
        f.write("\n")
        f.write("-"*60 + "\n")
        f.write("AI EXPLANATION METRICS\n")
        f.write("-"*60 + "\n\n")
        
        f.write(f"Explanations Generated: {provenance['statistics']['with_explanations']}\n")
        
        if latencies:
            stats = provenance['statistics']['explanation_latency']
            f.write(f"Min Latency: {stats['min_ms']}ms\n")
            f.write(f"Max Latency: {stats['max_ms']}ms\n")
            f.write(f"Avg Latency: {stats['avg_ms']}ms\n")
            f.write(f"Total Time: {stats['total_ms']}ms ({stats['total_ms']/1000:.2f}s)\n")
        
        f.write("\n")
        f.write("-"*60 + "\n")
        f.write("FEEDBACK (if available)\n")
        f.write("-"*60 + "\n\n")
        
        if feedback_stats:
            f.write(f"Total Feedback: {feedback_stats.get('total_feedback', 0)}\n")
            f.write(f"False Positive Rate: {feedback_stats.get('fp_rate', 0)*100:.1f}%\n")
            f.write(f"Helpful Rate: {feedback_stats.get('helpful_rate', 0)*100:.1f}%\n")
            f.write(f"Avg Clarity Rating: {feedback_stats.get('avg_clarity', 0):.2f}/5.0\n")
        else:
            f.write("No feedback data available\n")
        
        f.write("\n")
        f.write("="*60 + "\n")
        f.write(f"Export completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*60 + "\n")
    
    print(f"✅ Summary: {summary_file}")
    
    # Print summary
    print("\n📊 Provenance Summary:")
    print(f"   Findings: {len(findings)}")
    print(f"   With Explanations: {provenance['statistics']['with_explanations']}")
    if latencies:
        print(f"   Avg Explanation Time: {provenance['statistics']['explanation_latency']['avg_ms']}ms")
    
    return json_file


def export_all_runs(output_dir='outputs/provenance_all'):
    """Export provenance for all analysis runs"""
    db = Database()
    runs = db.get_recent_runs(limit=100)
    
    print(f"📦 Exporting provenance for {len(runs)} runs...")
    
    for run in runs:
        export_provenance(run['id'], output_dir)
    
    print(f"\n✅ All provenance exported to: {output_dir}")


def main():
    parser = argparse.ArgumentParser(description='Export ACR-QA Provenance Data')
    parser.add_argument('run_id', type=int, nargs='?', help='Analysis run ID (optional)')
    parser.add_argument('--all', action='store_true', help='Export all runs')
    parser.add_argument('-o', '--output', default='outputs/provenance', help='Output directory')
    
    args = parser.parse_args()
    
    try:
        if args.all:
            export_all_runs(args.output)
        else:
            export_provenance(args.run_id, args.output)
    except Exception as e:
        print(f"❌ Error exporting provenance: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()