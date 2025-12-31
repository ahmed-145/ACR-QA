#!/usr/bin/env python3
"""
Markdown Report Generator for ACR-QA v2.0
Creates human-readable reports from analysis runs
"""
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from DATABASE.database import Database
import argparse


def generate_report(run_id=None, output_file=None):
    """
    Generate markdown report for an analysis run
    
    Args:
        run_id: Analysis run ID (None = latest)
        output_file: Output file path (None = auto-generate)
    """
    db = Database()
    
    # Get run info
    if run_id:
        run = db.get_run_info(run_id)
        if not run:
            print(f"❌ Run {run_id} not found")
            return
    else:
        # Get latest run
        runs = db.get_recent_runs(limit=1)
        if not runs:
            print("❌ No analysis runs found")
            return
        run = runs[0]
        run_id = run['id']
    
    # Get findings with explanations
    findings = db.get_findings_with_explanations(run_id)
    
    # Group findings by severity and file
    findings_by_severity = {'error': [], 'warning': [], 'info': []}
    findings_by_file = {}
    
    for f in findings:
        severity = f['severity']
        if severity in findings_by_severity:
            findings_by_severity[severity].append(f)
        
        file_path = f['file_path']
        if file_path not in findings_by_file:
            findings_by_file[file_path] = []
        findings_by_file[file_path].append(f)
    
    # Generate report
    report_lines = []
    
    # Header
    report_lines.append("# ACR-QA v2.0 Analysis Report")
    report_lines.append("")
    report_lines.append("**Automated Code Review & Quality Assurance**")
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")
    
    # Run metadata
    report_lines.append("## 📊 Analysis Metadata")
    report_lines.append("")
    report_lines.append(f"- **Run ID:** {run['id']}")
    report_lines.append(f"- **Repository:** {run['repo_name']}")
    if run['pr_number']:
        report_lines.append(f"- **Pull Request:** #{run['pr_number']}")
    if run['commit_sha']:
        report_lines.append(f"- **Commit:** `{run['commit_sha']}`")
    if run['branch']:
        report_lines.append(f"- **Branch:** `{run['branch']}`")
    report_lines.append(f"- **Status:** {run['status']}")
    report_lines.append(f"- **Started:** {run['started_at']}")
    if run['completed_at']:
        report_lines.append(f"- **Completed:** {run['completed_at']}")
    report_lines.append("")
    
    # Executive summary
    report_lines.append("## 📈 Executive Summary")
    report_lines.append("")
    report_lines.append(f"**Total Issues Found:** {len(findings)}")
    report_lines.append("")
    
    report_lines.append("### Severity Breakdown")
    report_lines.append("")
    report_lines.append(f"- 🔴 **High (Errors):** {len(findings_by_severity['error'])}")
    report_lines.append(f"- 🟡 **Medium (Warnings):** {len(findings_by_severity['warning'])}")
    report_lines.append(f"- 🟢 **Low (Info):** {len(findings_by_severity['info'])}")
    report_lines.append("")
    
    # Category breakdown
    categories = {}
    for f in findings:
        cat = f['category']
        categories[cat] = categories.get(cat, 0) + 1
    
    report_lines.append("### Category Breakdown")
    report_lines.append("")
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        report_lines.append(f"- **{cat.replace('-', ' ').title()}:** {count}")
    report_lines.append("")
    
    # Files affected
    report_lines.append("### Files Analyzed")
    report_lines.append("")
    report_lines.append(f"**Total files with issues:** {len(findings_by_file)}")
    report_lines.append("")
    
    # Critical findings first
    if findings_by_severity['error']:
        report_lines.append("---")
        report_lines.append("")
        report_lines.append("## 🔴 Critical Issues (High Severity)")
        report_lines.append("")
        report_lines.append("⚠️ **These issues should be addressed immediately**")
        report_lines.append("")
        
        for i, finding in enumerate(findings_by_severity['error'], 1):
            report_lines.append(f"### {i}. {finding['rule_id']} - {finding['category']}")
            report_lines.append("")
            report_lines.append(f"**Location:** `{finding['file_path']}:{finding['line_number']}`")
            report_lines.append("")
            report_lines.append(f"**Tool:** {finding['tool']}")
            report_lines.append("")
            report_lines.append(f"**Issue:**")
            report_lines.append(f"> {finding['message']}")
            report_lines.append("")
            
            if finding.get('explanation_text'):
                report_lines.append(f"**AI Explanation:**")
                report_lines.append("")
                report_lines.append(finding['explanation_text'])
                report_lines.append("")
            
            report_lines.append("---")
            report_lines.append("")
    
    # Medium severity
    if findings_by_severity['warning']:
        report_lines.append("## 🟡 Medium Priority Issues")
        report_lines.append("")
        
        for i, finding in enumerate(findings_by_severity['warning'][:10], 1):  # Limit to 10
            report_lines.append(f"### {i}. {finding['rule_id']}")
            report_lines.append("")
            report_lines.append(f"**Location:** `{finding['file_path']}:{finding['line_number']}`")
            report_lines.append("")
            report_lines.append(f"**Message:** {finding['message']}")
            report_lines.append("")
            
            if finding.get('explanation_text'):
                # Truncate long explanations
                explanation = finding['explanation_text']
                if len(explanation) > 300:
                    explanation = explanation[:297] + "..."
                report_lines.append(f"**Explanation:** {explanation}")
                report_lines.append("")
            
            report_lines.append("---")
            report_lines.append("")
        
        if len(findings_by_severity['warning']) > 10:
            remaining = len(findings_by_severity['warning']) - 10
            report_lines.append(f"*... and {remaining} more medium-priority issues*")
            report_lines.append("")
    
    # Low severity summary
    if findings_by_severity['info']:
        report_lines.append("## 🟢 Low Priority Issues")
        report_lines.append("")
        report_lines.append(f"**Total:** {len(findings_by_severity['info'])}")
        report_lines.append("")
        report_lines.append("*Low priority issues include style violations, minor best-practice deviations, and informational findings. View the dashboard for full details.*")
        report_lines.append("")
    
    # Recommendations
    report_lines.append("---")
    report_lines.append("")
    report_lines.append("## 💡 Recommendations")
    report_lines.append("")
    
    if findings_by_severity['error']:
        report_lines.append("1. **Address critical issues immediately** - Focus on security and error-level findings")
    if findings_by_severity['warning']:
        report_lines.append("2. **Review medium-priority warnings** - These indicate potential bugs or maintainability issues")
    if findings_by_severity['info']:
        report_lines.append("3. **Consider fixing style issues** - Improves code consistency and readability")
    
    report_lines.append("")
    report_lines.append("## 📚 Resources")
    report_lines.append("")
    report_lines.append("- View interactive dashboard: `python3 app.py` → http://localhost:5000")
    report_lines.append("- Export full data: `python3 scripts/export_provenance.py " + str(run_id) + "`")
    report_lines.append("- Compute metrics: `python3 scripts/compute_metrics.py`")
    report_lines.append("")
    
    # Footer
    report_lines.append("---")
    report_lines.append("")
    report_lines.append(f"*Report generated by ACR-QA v2.0 on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    report_lines.append("")
    
    # Write report
    if not output_file:
        output_file = f"outputs/report_run_{run_id}.md"
    
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    print(f"✅ Report generated: {output_path}")
    print(f"   Total findings: {len(findings)}")
    print(f"   Critical: {len(findings_by_severity['error'])}")
    print(f"   Medium: {len(findings_by_severity['warning'])}")
    print(f"   Low: {len(findings_by_severity['info'])}")
    
    return output_path


def main():
    parser = argparse.ArgumentParser(description='Generate ACR-QA Analysis Report')
    parser.add_argument('run_id', type=int, nargs='?', help='Analysis run ID (optional, defaults to latest)')
    parser.add_argument('-o', '--output', help='Output file path')
    
    args = parser.parse_args()
    
    try:
        generate_report(args.run_id, args.output)
    except Exception as e:
        print(f"❌ Error generating report: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()