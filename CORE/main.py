#!/usr/bin/env python3
"""
ACR-QA v2.0 - Main Analysis Pipeline
Orchestrates: Detection → Explanation → Storage
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import subprocess
import sys
import argparse
from pathlib import Path
from DATABASE.database import Database
from CORE.engines.explainer import ExplanationEngine
from CORE.utils.code_extractor import extract_code_snippet

class AnalysisPipeline:
    def __init__(self, target_dir="samples/realistic-issues", files=None):
        self.target_dir = target_dir
        self.db = Database()
        self.explainer = ExplanationEngine()
        self.files = files  # NEW: specific files to analyze
        
    def run(self, repo_name="local", pr_number=None, limit=None, files=None):
        """Run full analysis pipeline"""
        print("🚀 ACR-QA v2.0 Analysis Pipeline")
        print("="*50)
        
        # Step 1: Create analysis run
        print("\n[1/4] Creating analysis run in database...")
        run_id = self.db.create_analysis_run(
            repo_name=repo_name,
            pr_number=pr_number
        )
        print(f"      ✓ Run ID: {run_id}")
        
        # Step 2: Run detection tools
        print("\n[2/4] Running detection tools...")
        print("      - Ruff (style & practices)")
        print("      - Semgrep (security & patterns)")
        print("      - Vulture (unused code)")
        print("      - jscpd (duplication)")
        
        # Check if analyzing specific files or entire directory
        if files:
            # Only analyze specific files (for PR diffs)
            print(f"      - Analyzing {len(files)} changed files")
            # TODO: Implement per-file analysis in future
            subprocess.run(['bash', 'TOOLS/run_checks.sh', self.target_dir], check=True)
        else:
            # Analyze entire directory
            subprocess.run(['bash', 'TOOLS/run_checks.sh', self.target_dir], check=True)
        
        print("      ✓ Detection complete")
        
        # Step 3: Load findings
        print("\n[3/4] Loading normalized findings...")
        findings = self._load_findings()
        total_findings = len(findings)
        print(f"      ✓ {total_findings} issues detected")
        
        # Step 4: Generate explanations
        print("\n[4/4] Generating AI explanations (Cerebras API)...")
        
        # Limit findings for demo/speed
        findings_to_process = findings[:limit] if limit else findings
        
        for i, finding in enumerate(findings_to_process, 1):
            print(f"      [{i}/{len(findings_to_process)}] {finding.get('canonical_rule_id', finding.get('rule_id', 'UNKNOWN'))}", end=" ")
            
            try:
                # Insert finding into DB
                finding_id = self.db.insert_finding(run_id, finding)
                
                # Extract code snippet
                snippet = extract_code_snippet(
                    finding['file'], 
                    finding['line'],
                    context_lines=3
                )
                
                # Generate explanation
                explanation = self.explainer.generate_explanation(finding, snippet)
                
                # Store explanation
                self.db.insert_explanation(finding_id, explanation)
                
                print(f"✓ ({explanation['latency_ms']}ms)")
                
            except Exception as e:
                print(f"✗ Error: {e}")
        
        # Mark run as complete
        self.db.complete_analysis_run(run_id, total_findings)
        
        # Save run ID to file for GitHub Actions
        try:
            with open('/tmp/acr_run_id.txt', 'w') as f:
                f.write(str(run_id))
        except:
            pass  # Don't fail if can't write file
        
        print("\n" + "="*50)
        print(f"✅ Analysis Complete!")
        print(f"   Run ID: {run_id}")
        print(f"   Total Findings: {total_findings}")
        print(f"   Explanations Generated: {len(findings_to_process)}")
        print("\nNext Steps:")
        print(f"   View results: python scripts/dashboard.py")
        print(f"   Generate report: python scripts/generate_report.py {run_id}")
        print(f"   Export data: python scripts/export_provenance.py {run_id}")
        
        return run_id
    
    def _load_findings(self):
    # Import normalizer
        from CORE.engines.normalizer import normalize_all

        # Run normalization
        print("      - Normalizing tool outputs...")
        findings = normalize_all('DATA/outputs')  # ✅ CORRECT PATH!
        
        # Save to JSON for caching
        with open('DATA/outputs/findings.json', 'w') as f:
            json.dump([f.to_dict() for f in findings], f, indent=2)
        
        return [f.to_dict() for f in findings]

def main():
    parser = argparse.ArgumentParser(description='ACR-QA v2.0 Analysis Pipeline')
    parser.add_argument('--target-dir', default='samples/realistic-issues', 
                        help='Directory to analyze')
    parser.add_argument('--repo-name', default='local', 
                        help='Repository name')
    parser.add_argument('--pr-number', type=int, 
                        help='Pull request number')
    parser.add_argument('--limit', type=int, default=10,
                        help='Limit explanations (for speed)')
    
    args = parser.parse_args()
    
    pipeline = AnalysisPipeline(target_dir=args.target_dir)
    pipeline.run(
        repo_name=args.repo_name,
        pr_number=args.pr_number,
        limit=args.limit
    )

if __name__ == '__main__':
    main()