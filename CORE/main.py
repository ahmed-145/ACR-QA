#!/usr/bin/env python3
"""
ACR-QA v2.4 - Main Analysis Pipeline
Orchestrates: Detection → Normalization → Config Filtering → Quality Gate → Explanation → Storage
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import json
import os
import shutil
import subprocess
import tempfile

from CORE.config_loader import ConfigLoader
from CORE.engines.explainer import ExplanationEngine
from CORE.engines.quality_gate import QualityGate
from CORE.utils.code_extractor import extract_code_snippet
from CORE.utils.rate_limiter import get_rate_limiter
from DATABASE.database import Database


class AnalysisPipeline:
    def __init__(self, target_dir="samples/realistic-issues", files=None):
        self.target_dir = target_dir
        self.db = Database()
        self.explainer = ExplanationEngine()
        self.files = files
        # Load per-repo config (.acrqa.yml)
        self.config = ConfigLoader(project_dir=target_dir).load()

    def run(self, repo_name="local", pr_number=None, limit=None, files=None):
        """Run full analysis pipeline"""
        print("🚀 ACR-QA v2.4 Analysis Pipeline")
        print("=" * 50)

        # Step 0: Check rate limit
        print("\n[0/5] Checking rate limit...")
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))

        rate_limiter = get_rate_limiter(redis_host=redis_host, redis_port=redis_port)
        allowed, retry_after = rate_limiter.check_rate_limit(repo_name, pr_number)

        if not allowed:
            print("      ✗ RATE LIMITED!")
            print(f"      Repository: {repo_name}")
            if pr_number:
                print(f"      PR Number: {pr_number}")
            print(f"      Retry after: {retry_after:.1f} seconds")
            print("\n⚠️  Rate limit: ≤1 analysis per repo per minute")
            print(f"    Please wait {retry_after:.1f}s before retrying.")
            return None

        print("      ✓ Rate limit OK")

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
            analysis_dir = tempfile.mkdtemp(prefix="acrqa_diff_")
            try:
                for f in files:
                    src = Path(f)
                    if src.exists():
                        dest = Path(analysis_dir) / src.name
                        shutil.copy2(str(src), str(dest))
                subprocess.run(
                    ["bash", "TOOLS/run_checks.sh", analysis_dir], check=True
                )
            finally:
                shutil.rmtree(analysis_dir, ignore_errors=True)
        else:
            subprocess.run(["bash", "TOOLS/run_checks.sh", self.target_dir], check=True)

        print("      ✓ Detection complete")

        # Step 2b: Run extra scanners (secrets + SCA)
        print("\n[2b/5] Running extra scanners...")
        target = analysis_dir if files and "analysis_dir" in dir() else self.target_dir
        extra_findings = self.run_extra_scanners(target)
        print(f"      ✓ {len(extra_findings)} extra findings from secrets/SCA")

        # Step 3: Load and filter findings
        print("\n[3/5] Loading normalized findings...")
        findings = self._load_findings()

        # Apply config filters: disabled rules, ignored paths, min severity
        findings = self._apply_config_filters(findings)

        # Deduplicate findings (same file+line+rule from different tools)
        findings = self._deduplicate_findings(findings)

        total_findings = len(findings)
        print(f"      ✓ {total_findings} issues after filtering & dedup")

        # Step 4: Generate AI explanations (with caching)
        print("[4/5] Generating AI explanations (Cerebras API)...")

        redis_client = (
            rate_limiter.redis if rate_limiter and rate_limiter.redis else None
        )
        ExplanationEngine(redis_client=redis_client)

        # Cap explanations using config
        max_explanations = self.config.get("ai", {}).get("max_explanations", 50)
        effective_limit = min(limit, max_explanations) if limit else max_explanations
        findings_to_process = (
            findings[:effective_limit] if effective_limit else findings
        )

        for i, finding in enumerate(findings_to_process, 1):
            print(
                f"      [{i}/{len(findings_to_process)}] {finding.get('canonical_rule_id', finding.get('rule_id', 'UNKNOWN'))}",
                end=" ",
            )

            try:
                finding_id = self.db.insert_finding(run_id, finding)
                snippet = extract_code_snippet(
                    finding["file"], finding["line"], context_lines=3
                )
                explanation = self.explainer.generate_explanation(finding, snippet)
                self.db.insert_explanation(finding_id, explanation)
                print(f"✓ ({explanation['latency_ms']}ms)")
            except Exception as e:
                print(f"✗ Error: {e}")

        # Mark run as complete
        self.db.complete_analysis_run(run_id, total_findings)

        # Save run ID for GitHub Actions
        try:
            with open("/tmp/acr_run_id.txt", "w") as f:
                f.write(str(run_id))
        except:
            pass

        # Step 5: Quality Gate
        print("\n[5/5] Quality Gate evaluation...")
        gate = QualityGate(config=self.config)
        gate_result = gate.evaluate(findings)
        gate.print_report(gate_result)

        # Print summary
        print(f"\n   Run ID: {run_id}")
        print(f"   Explanations Generated: {len(findings_to_process)}")
        print("\nNext Steps:")
        print("   View dashboard: python3 FRONTEND/app.py")
        print(f"   Generate report: python3 scripts/generate_report.py {run_id}")
        print(f"   Export SARIF: python3 scripts/export_sarif.py --run-id {run_id}")

        # Return exit code info
        self._gate_passed = gate_result["passed"]
        return run_id

    def _apply_config_filters(self, findings):
        """Filter findings based on .acrqa.yml configuration."""
        loader = ConfigLoader.__new__(ConfigLoader)
        loader.project_dir = Path(self.target_dir)
        loader._config = self.config

        filtered = []
        removed_rules = 0
        removed_paths = 0
        removed_severity = 0

        min_sev = self.config.get("reporting", {}).get("min_severity", "low")
        sev_order = {"high": 3, "medium": 2, "low": 1}
        min_sev_level = sev_order.get(min_sev, 1)

        for f in findings:
            rule_id = f.get("canonical_rule_id", f.get("rule_id", ""))

            # Check if rule is disabled
            if not loader.is_rule_enabled(rule_id):
                removed_rules += 1
                continue

            # Check if file path is ignored
            file_path = f.get("file_path", f.get("file", ""))
            if loader.should_ignore_path(file_path):
                removed_paths += 1
                continue

            # Check minimum severity
            sev = f.get("canonical_severity", f.get("severity", "low")).lower()
            if sev_order.get(sev, 1) < min_sev_level:
                removed_severity += 1
                continue

            # Apply severity overrides
            override = loader.get_severity_override(rule_id)
            if override:
                f["canonical_severity"] = override
                f["severity"] = override

            filtered.append(f)

        if removed_rules or removed_paths or removed_severity:
            print(
                f"      - Config filters: removed {removed_rules} disabled rules, "
                f"{removed_paths} ignored paths, {removed_severity} below min severity"
            )

        return filtered

    def _deduplicate_findings(self, findings):
        """Remove duplicate findings (same file + line + canonical rule from different tools)."""
        seen = {}
        # Priority: security tools > specialized > general
        tool_priority = {
            "bandit": 3,
            "semgrep": 3,
            "secrets": 3,
            "vulture": 2,
            "radon": 2,
            "ruff": 1,
            "jscpd": 1,
        }

        for f in findings:
            file_path = f.get("file_path", f.get("file", ""))
            line = f.get("line_number", f.get("line", 0))
            rule = f.get("canonical_rule_id", f.get("rule_id", ""))
            key = (file_path, line, rule)

            if key not in seen:
                seen[key] = f
            else:
                # Keep finding from higher-priority tool
                existing_tool = seen[key].get("tool", "")
                new_tool = f.get("tool", "")
                if tool_priority.get(new_tool, 0) > tool_priority.get(existing_tool, 0):
                    seen[key] = f

        deduped = list(seen.values())
        removed = len(findings) - len(deduped)
        if removed:
            print(f"      - Dedup: removed {removed} duplicate findings")
        return deduped

    def run_autofix(self, findings):
        """Run autofix engine on findings and display diffs."""
        from CORE.engines.autofix import AutoFixEngine

        engine = AutoFixEngine()
        fixable = [
            f for f in findings if engine.can_fix(f.get("canonical_rule_id", ""))
        ]
        if not fixable:
            print("\n⚙️  No auto-fixable issues found.")
            return []

        print(f"\n⚙️  Auto-Fix: {len(fixable)} fixable issues found")
        results = []
        for f in fixable:
            rule_id = f.get("canonical_rule_id", "")
            filepath = f.get("file_path", f.get("file", ""))
            line = f.get("line_number", f.get("line", 0))
            confidence = engine.get_fix_confidence(rule_id)

            try:
                finding_dict = {
                    "canonical_rule_id": rule_id,
                    "file_path": filepath,
                    "line": line,
                    "message": f.get("message", ""),
                }
                fix = engine.generate_fix(finding_dict)
                if fix and fix.get("fixed") is not None:
                    results.append(
                        {
                            "rule_id": rule_id,
                            "file": filepath,
                            "line": line,
                            "confidence": confidence,
                            "original": fix.get("original", ""),
                            "fixed": fix.get("fixed", ""),
                        }
                    )
                    print(
                        f"   ✓ {rule_id} @ {filepath}:{line} (confidence: {confidence})"
                    )
            except Exception as e:
                print(f"   ✗ {rule_id} @ {filepath}:{line} — {e}")

        if results:
            print(f"\n   📋 {len(results)} fixes generated. Review diffs above.")
        return results

    def run_extra_scanners(self, target_dir):
        """Run secrets detection and SCA scanning as part of the pipeline."""
        extra_findings = []

        try:
            from CORE.engines.secrets_detector import SecretsDetector

            print("      - Secrets Detector (hardcoded credentials)")
            detector = SecretsDetector()
            results = detector.scan_directory(target_dir)
            if results.get("findings"):
                canonical = detector.to_canonical_findings(results["findings"])
                extra_findings.extend(canonical)
                print(f"        → {len(results['findings'])} secrets found")
            else:
                print("        → Clean (no secrets)")
        except Exception as e:
            print(f"        ✗ Secrets scan error: {e}")

        try:
            from CORE.engines.sca_scanner import SCAScanner

            print("      - SCA Scanner (dependency vulnerabilities)")
            scanner = SCAScanner(project_dir=target_dir)
            results = scanner.scan()
            if results.get("vulnerabilities"):
                extra_findings.extend(results.get("findings", []))
                print(
                    f"        → {len(results['vulnerabilities'])} vulnerabilities found"
                )
            else:
                print("        → Clean (no known vulnerabilities)")
        except Exception as e:
            print(f"        ✗ SCA scan error: {e}")

        return extra_findings

    def _load_findings(self):
        from CORE.engines.normalizer import normalize_all

        print("      - Normalizing tool outputs...")
        findings = normalize_all("DATA/outputs")

        with open("DATA/outputs/findings.json", "w") as f:
            json.dump([f.to_dict() for f in findings], f, indent=2)

        return [f.to_dict() for f in findings]


def get_diff_files(base_branch: str = "main") -> list:
    """Get changed Python files from git diff against base branch."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=ACM", base_branch],
            capture_output=True,
            text=True,
            check=True,
        )
        files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
        py_files = [f for f in files if f.endswith(".py")]
        return py_files
    except subprocess.CalledProcessError:
        print("⚠️ Could not get git diff. Analyzing full directory instead.")
        return []


def main():
    parser = argparse.ArgumentParser(description="ACR-QA v2.4 Analysis Pipeline")
    parser.add_argument(
        "--target-dir", default="samples/realistic-issues", help="Directory to analyze"
    )
    parser.add_argument("--repo-name", default="local", help="Repository name")
    parser.add_argument("--pr-number", type=int, help="Pull request number")
    parser.add_argument(
        "--limit", type=int, default=None, help="Limit explanations (for speed)"
    )
    parser.add_argument(
        "--diff-only",
        action="store_true",
        help="Only analyze files changed in git diff (PR diff mode)",
    )
    parser.add_argument(
        "--diff-base",
        default="main",
        help="Base branch for diff comparison (default: main)",
    )
    parser.add_argument(
        "--auto-fix",
        action="store_true",
        help="Generate auto-fix suggestions for fixable issues",
    )

    args = parser.parse_args()

    # Determine files to analyze
    files = None
    if args.diff_only:
        files = get_diff_files(args.diff_base)
        if files:
            print(f"📝 Diff-only mode: {len(files)} changed Python files")
            for f in files:
                print(f"   • {f}")
        else:
            print("📝 No changed Python files found. Running full analysis.")

    pipeline = AnalysisPipeline(target_dir=args.target_dir, files=files)
    run_id = pipeline.run(
        repo_name=args.repo_name,
        pr_number=args.pr_number,
        limit=args.limit,
        files=files,
    )

    # Run auto-fix if requested
    if args.auto_fix and run_id:
        findings_path = Path("DATA/outputs/findings.json")
        if findings_path.exists():
            import json as json_mod

            with open(findings_path) as fp:
                findings = json_mod.load(fp)
            pipeline.run_autofix(findings)

    # Exit with non-zero code if quality gate failed
    if run_id and hasattr(pipeline, "_gate_passed") and not pipeline._gate_passed:
        print("\n❌ Exiting with code 1 (quality gate failed)")
        sys.exit(1)


if __name__ == "__main__":
    main()
