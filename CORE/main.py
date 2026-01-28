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
import argparse
import os
from DATABASE.database import Database
from CORE.engines.explainer import ExplanationEngine
from CORE.utils.code_extractor import extract_code_snippet
from CORE.utils.rate_limiter import get_rate_limiter


class AnalysisPipeline:
    def __init__(self, target_dir="samples/realistic-issues", files=None):
        self.target_dir = target_dir
        self.db = Database()
        self.explainer = ExplanationEngine()
        self.files = files  # NEW: specific files to analyze

    def run(self, repo_name="local", pr_number=None, limit=None, files=None):
        """Run full analysis pipeline"""
        print("🚀 ACR-QA v2.0 Analysis Pipeline")
        print("=" * 50)

        # Step 0: Check rate limit
        print("\n[0/4] Checking rate limit...")
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))

        rate_limiter = get_rate_limiter(redis_host=redis_host, redis_port=redis_port)
        allowed, retry_after = rate_limiter.check_rate_limit(repo_name, pr_number)

        if not allowed:
            print(f"      ✗ RATE LIMITED!")
            print(f"      Repository: {repo_name}")
            if pr_number:
                print(f"      PR Number: {pr_number}")
            print(f"      Retry after: {retry_after:.1f} seconds")
            print(f"\n⚠️  Rate limit: ≤1 analysis per repo per minute")
            print(f"    Please wait {retry_after:.1f}s before retrying.")
            return None

        print(f"      ✓ Rate limit OK")

        # Step 1: Create analysis run
        print("\n[1/5] Creating analysis run in database...")
        run_id = self.db.create_analysis_run(repo_name=repo_name, pr_number=pr_number)
        print(f"      ✓ Run ID: {run_id}")

        # Step 2: Run detection tools
        print("\n[2/5] Running detection tools...")
        print("      - Ruff (style & practices)")
        print("      - Semgrep (security & patterns)")
        print("      - Vulture (unused code)")
        print("      - jscpd (duplication)")

        # Check if analyzing specific files or entire directory
        if files:
            # Only analyze specific files (for PR diffs)
            print(f"      - Analyzing {len(files)} changed files")
            # NOTE: Per-file analysis optimization deferred to Phase 2
            # Currently runs full directory scan for simplicity and tool compatibility
            subprocess.run(["bash", "TOOLS/run_checks.sh", self.target_dir], check=True)
        else:
            # Analyze entire directory
            subprocess.run(["bash", "TOOLS/run_checks.sh", self.target_dir], check=True)

        print("      ✓ Detection complete")

        # Step 3: Load findings
        print("\n[3/5] Loading normalized findings...")
        findings = self._load_findings()
        total_findings = len(findings)
        print(f"      ✓ {total_findings} issues detected")

        # Step 4: Generate AI explanations (with caching)
        print("[4/5] Generating AI explanations (Cerebras API)...")

        # Pass Redis client for caching (Phase 2 feature)
        redis_client = rate_limiter.redis if rate_limiter and rate_limiter.redis else None
        explainer = ExplanationEngine(redis_client=redis_client)

        # Limit findings for demo/speed
        findings_to_process = findings[:limit] if limit else findings

        for i, finding in enumerate(findings_to_process, 1):
            print(
                f"      [{i}/{len(findings_to_process)}] {finding.get('canonical_rule_id', finding.get('rule_id', 'UNKNOWN'))}",
                end=" ",
            )

            try:
                # Insert finding into DB
                finding_id = self.db.insert_finding(run_id, finding)

                # Extract code snippet
                snippet = extract_code_snippet(
                    finding["file"], finding["line"], context_lines=3
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
            with open("/tmp/acr_run_id.txt", "w") as f:
                f.write(str(run_id))
        except:
            pass  # Don't fail if can't write file

        print("\n" + "=" * 50)
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
        findings = normalize_all("DATA/outputs")  # ✅ CORRECT PATH!

        # Save to JSON for caching
        with open("DATA/outputs/findings.json", "w") as f:
            json.dump([f.to_dict() for f in findings], f, indent=2)

        return [f.to_dict() for f in findings]


def main():
    parser = argparse.ArgumentParser(description="ACR-QA v2.0 Analysis Pipeline")
    parser.add_argument(
        "--target-dir", default="samples/realistic-issues", help="Directory to analyze"
    )
    parser.add_argument("--repo-name", default="local", help="Repository name")
    parser.add_argument("--pr-number", type=int, help="Pull request number")
    parser.add_argument(
        "--limit", type=int, default=10, help="Limit explanations (for speed)"
    )

    args = parser.parse_args()

    pipeline = AnalysisPipeline(target_dir=args.target_dir)
    pipeline.run(repo_name=args.repo_name, pr_number=args.pr_number, limit=args.limit)


if __name__ == "__main__":
    main()
