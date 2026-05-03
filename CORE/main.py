#!/usr/bin/env python3
"""
ACR-QA v3.2.4 - Main Analysis Pipeline
Orchestrates: Detection → Normalization → Config Filtering → Quality Gate → Explanation → Storage
"""

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def setup_logging(verbose=False, quiet=False):
    level = logging.INFO
    if verbose:
        level = logging.DEBUG
    elif quiet:
        level = logging.WARNING

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers to avoid duplicates, except pytest caplog
    for handler in root_logger.handlers[:]:
        if "LogCapture" not in type(handler).__name__:
            root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    if os.getenv("ACRQA_JSON_LOGS") == "1":

        class JsonFormatter(logging.Formatter):
            def format(self, record):
                log_record = {
                    "timestamp": self.formatTime(record, self.datefmt),
                    "level": record.levelname,
                    "module": record.module,
                    "message": record.getMessage(),
                }
                import json

                return json.dumps(log_record)

        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(message)s"))

    root_logger.addHandler(handler)


logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent))

from CORE.config_loader import ConfigLoader  # noqa: E402
from CORE.engines.explainer import ExplanationEngine  # noqa: E402
from CORE.engines.quality_gate import QualityGate  # noqa: E402
from CORE.utils.code_extractor import extract_code_snippet  # noqa: E402
from CORE.utils.rate_limiter import get_rate_limiter  # noqa: E402
from DATABASE.database import Database  # noqa: E402


class AnalysisPipeline:
    def __init__(self, target_dir="samples/realistic-issues", files=None):
        self.target_dir = target_dir
        self.db = Database()
        self.explainer = ExplanationEngine()
        self.files = files
        # Load per-repo config (.acrqa.yml)
        self.config = ConfigLoader(project_dir=target_dir).load()

    def run(self, repo_name="local", pr_number=None, limit=None, files=None, rich_output=False, baseline_run_id=None):
        """Run full analysis pipeline."""
        logger.info("🚀 ACR-QA v3.2.4 Analysis Pipeline")
        logger.info("=" * 50)

        # Step 0: Check rate limit
        logger.info("\n[0/5] Checking rate limit...")
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))

        rate_limiter = get_rate_limiter(redis_host=redis_host, redis_port=redis_port)
        allowed, retry_after = rate_limiter.check_rate_limit(repo_name, pr_number)

        if not allowed:
            logger.error("      ✗ RATE LIMITED!")
            logger.info(f"      Repository: {repo_name}")
            if pr_number:
                logger.info(f"      PR Number: {pr_number}")
            logger.info(f"      Retry after: {retry_after:.1f} seconds")
            logger.info("\n⚠️  Rate limit: ≤1 analysis per repo per minute")
            logger.info(f"    Please wait {retry_after:.1f}s before retrying.")
            return None

        logger.info("      ✓ Rate limit OK")

        # Step 1: Create analysis run
        logger.info("\n[1/5] Creating analysis run in database...")
        run_id = self.db.create_analysis_run(repo_name=repo_name, pr_number=pr_number)
        logger.info(f"      ✓ Run ID: {run_id}")

        # Step 2: Run detection tools
        logger.info("\n[2/5] Running detection tools...")
        logger.info("      - Ruff (style & practices)")
        logger.info("      - Semgrep (security & patterns)")
        logger.info("      - Vulture (unused code)")
        logger.info("      - jscpd (duplication)")

        # Check if analyzing specific files or entire directory
        if files:
            # Only analyze specific files (for PR diffs)
            logger.info(f"      - Analyzing {len(files)} changed files")
            analysis_dir = tempfile.mkdtemp(prefix="acrqa_diff_")
            try:
                for f in files:
                    src = Path(f)
                    if src.exists():
                        dest = Path(analysis_dir) / src.name
                        shutil.copy2(str(src), str(dest))
                subprocess.run(["bash", "TOOLS/run_checks.sh", analysis_dir], check=True)
            finally:
                shutil.rmtree(analysis_dir, ignore_errors=True)
        else:
            subprocess.run(["bash", "TOOLS/run_checks.sh", self.target_dir], check=True)

        logger.info("      ✓ Detection complete")

        # Step 2b: Run extra scanners (secrets + SCA)
        logger.info("\n[2b/5] Running extra scanners...")
        target = analysis_dir if files and "analysis_dir" in dir() else self.target_dir
        extra_findings = self.run_extra_scanners(target)
        logger.info(f"      ✓ {len(extra_findings)} extra findings from secrets/SCA")

        # Step 3: Load and filter findings
        logger.info("\n[3/5] Loading normalized findings...")
        findings = self._load_findings()

        # Apply config filters: disabled rules, ignored paths, min severity
        findings = self._apply_config_filters(findings)

        # Triage Memory: suppress findings that match learned FP rules (Feature 6)
        from CORE.engines.triage_memory import TriageMemory

        findings, suppressed = TriageMemory().suppress_findings(findings, self.db)
        if suppressed:
            logger.info(f"      - Triage Memory: suppressed {suppressed} known false positive(s)")

        # Deduplicate findings (same file+line+rule from different tools)
        findings = self._deduplicate_findings(findings)

        # Cap findings per rule (max 5 per rule to prevent flooding)
        findings = self._cap_per_rule(findings, max_per_rule=5)

        # Sort findings: security/high first so they get explained within the limit
        findings = self._sort_by_priority(findings)

        total_findings = len(findings)
        logger.info(f"      ✓ {total_findings} issues after filtering & dedup")

        # Baseline comparison
        if baseline_run_id:
            logger.info(f"\n[3.5/5] Comparing against baseline run ID {baseline_run_id}...")
            baseline_findings = self.db.get_findings(run_id=baseline_run_id, limit=10000)
            baseline_fingerprints = set()
            for bf in baseline_findings:
                # Use DB fingerprint if added later, else recalculate
                fp = bf.get("fingerprint")
                if not fp:
                    import hashlib

                    evidence = bf.get("evidence", {})
                    if isinstance(evidence, str):
                        import json

                        try:
                            evidence = json.loads(evidence)
                        except:
                            evidence = {}
                    snippet = evidence.get("snippet", "")[:200]
                    raw = f"{bf.get('canonical_rule_id')}:{bf.get('file_path')}:{snippet}"
                    fp = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
                baseline_fingerprints.add(fp)

            new_findings_count = 0
            for f in findings:
                f_fp = f.get("fingerprint")
                if not f_fp:
                    import hashlib

                    snippet = f.get("evidence", {}).get("snippet", "")[:200]
                    raw = f"{f.get('canonical_rule_id')}:{f.get('file_path', f.get('file', ''))}:{snippet}"
                    f_fp = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
                    f["fingerprint"] = f_fp

                if f_fp in baseline_fingerprints:
                    f["is_new"] = False
                else:
                    f["is_new"] = True
                    new_findings_count += 1

            logger.info(
                f"      ✓ Delta summary: {new_findings_count} new findings, {len(findings) - new_findings_count} existing."
            )
        else:
            for f in findings:
                f["is_new"] = True

        # Step 4: Generate AI explanations (with caching)
        logger.info("[4/5] Generating AI explanations (Groq API)...")

        redis_client = rate_limiter.redis if rate_limiter and rate_limiter.redis else None
        self.explainer = ExplanationEngine(redis_client=redis_client)

        # Cap explanations using config
        max_explanations = self.config.get("ai", {}).get("max_explanations", 50)
        effective_limit = min(limit, max_explanations) if limit else max_explanations
        findings_to_process = findings[:effective_limit] if effective_limit else findings

        findings_with_snippets = []
        for f in findings_to_process:
            f["_db_id"] = self.db.insert_finding(run_id, f)
            snippet = extract_code_snippet(
                f["file_path"] if "file_path" in f else f["file"], f["line"], context_lines=3
            )
            findings_with_snippets.append({"finding": f, "snippet": snippet})

        logger.info(f"      Batching {len(findings_with_snippets)} explanations...")

        start_time = time.time()
        explanations = self.explainer.generate_explanation_batch(findings_with_snippets)
        total_time = int((time.time() - start_time) * 1000)

        logger.info(f"✓ ({total_time}ms total)")

        for i, (f_data, expl) in enumerate(zip(findings_with_snippets, explanations, strict=False), 1):
            f = f_data["finding"]
            rule_id = f.get("canonical_rule_id", f.get("rule_id", "UNKNOWN"))

            # If gather caught an exception, it might be an Exception object
            if isinstance(expl, Exception):
                logger.error(f"      [{i}/{len(findings_to_process)}] {rule_id} ✗ Error: {expl}")
                # Provide a fallback
                fallback_expl = {
                    "model_name": self.explainer.model,
                    "prompt_filled": "",
                    "response_text": self.explainer.get_fallback_explanation(f),
                    "temperature": self.explainer.temperature,
                    "max_tokens": self.explainer.max_tokens,
                    "tokens_used": None,
                    "latency_ms": 0,
                    "cost_usd": 0,
                    "status": "fallback",
                    "error": str(expl),
                }
                self.db.insert_explanation(f["_db_id"], fallback_expl)
            else:
                latency = expl.get("latency_ms", 0)
                logger.info(f"      [{i}/{len(findings_to_process)}] {rule_id} ✓ ({latency}ms)")
                self.db.insert_explanation(f["_db_id"], expl)

        # Mark run as complete
        self.db.complete_analysis_run(run_id, total_findings)

        # Save run ID for GitHub Actions
        try:
            with open("/tmp/acr_run_id.txt", "w") as f:
                f.write(str(run_id))
        except OSError:
            pass

        # Step 5: Quality Gate
        logger.info("\n[5/5] Quality Gate evaluation...")
        gate = QualityGate(config=self.config)
        gate_result = gate.evaluate(findings)

        if rich_output:
            self._print_rich_output(findings, gate_result, run_id, len(findings_to_process))
        else:
            gate.print_report(gate_result)
            logger.info(f"\n   Run ID: {run_id}")
            logger.info(f"   Explanations Generated: {len(findings_to_process)}")
            logger.info("\nNext Steps:")
            logger.info("   View dashboard: python3 FRONTEND/app.py")
            logger.info(f"   Generate report: python3 scripts/generate_report.py {run_id}")
            logger.info(f"   Export SARIF: python3 scripts/export_sarif.py --run-id {run_id}")

        # Return exit code info
        # Feature 9: Cross-language correlation
        try:
            from CORE.engines.cross_language_correlator import CrossLanguageCorrelator

            correlator = CrossLanguageCorrelator(str(self.target_dir))
            findings, corr_groups = correlator.enrich_findings(findings)
            if corr_groups:
                logger.info(f"\n[+] Cross-language correlations: {len(corr_groups)} chain(s) detected")
                for g in corr_groups:
                    logger.info(f"    [{g.combined_severity.upper()}] {g.correlation_type}: {g.chain_description[:80]}")

                # Save correlation results to the database
                for f in findings:
                    if "_db_id" in f and "correlation_chain" in f:
                        evidence = f.get("evidence", {})
                        if isinstance(evidence, str):
                            import json

                            try:
                                evidence = json.loads(evidence)
                            except Exception:
                                evidence = {}
                        evidence["correlation_chain"] = f["correlation_chain"]
                        evidence["correlation_severity"] = f.get("correlation_severity", "high")

                        self.db.update_finding_correlation(
                            finding_id=f["_db_id"], confidence_score=f.get("confidence_score"), evidence=evidence
                        )
        except Exception as e:
            logger.error(f"Cross-language correlation error: {e}")

        self._gate_passed = not gate.should_block(gate_result)
        self._gate_comment = gate.format_gate_comment(gate_result)
        return run_id

    def _print_rich_output(self, findings, gate_result, run_id, num_explained):
        """Display findings using Rich library for beautiful terminal output."""
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table

        console = Console()

        # ── Findings Table ──
        table = Table(
            title="🔍 ACR-QA Analysis Results",
            show_lines=True,
            title_style="bold cyan",
            border_style="dim",
        )
        table.add_column("#", style="dim", width=4, justify="right")
        table.add_column("Severity", width=10, justify="center")
        table.add_column("Rule", style="cyan", width=16)
        table.add_column("Category", width=12)
        table.add_column("File", style="blue")
        table.add_column("Line", width=6, justify="right")
        table.add_column("Message", style="white", max_width=50)

        severity_colors = {"high": "red bold", "medium": "yellow", "low": "green"}
        severity_icons = {"high": "🔴", "medium": "🟡", "low": "🟢"}

        for i, f in enumerate(findings[:50], 1):
            sev = f.get("canonical_severity", f.get("severity", "low")).lower()
            rule = f.get("canonical_rule_id", f.get("rule_id", "UNKNOWN"))
            cat = f.get("category", "unknown")
            filepath = f.get("file", "unknown")
            # Shorten file path for display
            if len(filepath) > 35:
                filepath = "..." + filepath[-32:]
            line = str(f.get("line", "?"))
            msg = f.get("message", f.get("description", ""))[:50]

            icon = severity_icons.get(sev, "⚪")
            color = severity_colors.get(sev, "white")

            table.add_row(
                str(i),
                f"[{color}]{icon} {sev.upper()}[/{color}]",
                rule,
                cat,
                filepath,
                line,
                msg,
            )

        if len(findings) > 50:
            table.add_row(
                "...",
                "",
                f"[dim]+{len(findings) - 50} more[/dim]",
                "",
                "",
                "",
                "",
            )

        console.print()
        console.print(table)

        # ── Quality Gate Panel ──
        counts = gate_result["counts"]
        status = "[green bold]✅ PASSED[/green bold]" if gate_result["passed"] else "[red bold]❌ FAILED[/red bold]"
        checks_text = ""
        for check in gate_result["checks"]:
            icon = "✅" if check["passed"] else "❌"
            checks_text += f"  {icon} {check['message']}\n"

        gate_content = (
            f"  Status: {status}\n"
            f"  Total: {counts['total']}  │  "
            f"🔴 High: {counts['high']}  │  "
            f"🟡 Medium: {counts['medium']}  │  "
            f"🟢 Low: {counts['low']}\n\n"
            f"{checks_text}\n"
            f"  [dim]Run ID: {run_id}  │  Explanations: {num_explained}[/dim]\n"
            f"  [dim]Dashboard: python3 FRONTEND/app.py[/dim]\n"
            f"  [dim]Report: python3 scripts/generate_report.py {run_id}[/dim]\n"
            f"  [dim]SARIF: python3 scripts/export_sarif.py --run-id {run_id}[/dim]"
        )

        panel = Panel(
            gate_content,
            title="🚦 Quality Gate",
            border_style="green" if gate_result["passed"] else "red",
            padding=(1, 2),
        )
        console.print(panel)

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
            logger.info(
                f"      - Config filters: removed {removed_rules} disabled rules, "
                f"{removed_paths} ignored paths, {removed_severity} below min severity"
            )

        return filtered

    def _deduplicate_findings(self, findings):
        """Remove duplicate findings from multiple tools on the same line.

        Two-pass approach:
        1. Exact dedup: same file + line + canonical rule → keep higher-priority tool
        2. Cross-tool dedup: same file + line + same security category → keep higher-priority tool
           This catches Semgrep CUSTOM-shell-injection + Bandit SECURITY-024 on the same line.
        """
        # Tool priority: prefer Bandit/Semgrep over general linters
        tool_priority = {
            "bandit": 3,
            "semgrep": 3,
            "secrets": 3,
            "vulture": 2,
            "radon": 2,
            "ruff": 1,
            "jscpd": 1,
        }

        # Cross-tool category groups — rules that detect the same class of issue
        CROSS_TOOL_GROUPS = {
            "shell-injection": {
                "SECURITY-020",
                "SECURITY-021",
                "SECURITY-024",
                "SECURITY-025",
                "CUSTOM-shell-injection",
                "CUSTOM-command-injection",
            },
            "pickle-unsafe": {"SECURITY-008", "CUSTOM-unsafe-pickle"},
            "eval-exec": {"SECURITY-001", "CUSTOM-dangerous-eval-usage"},
            "hardcoded-password": {"SECURITY-005", "CUSTOM-hardcoded-password", "HARDCODE-001"},
            "sql-injection": {"SECURITY-027", "CUSTOM-sql-injection"},
            "weak-hash-md5": {"SECURITY-009", "CRYPTO-001"},
            "bare-except": {"EXCEPT-001", "CUSTOM-bare-except"},
        }

        # Build reverse lookup: rule_id → group_name
        rule_to_group = {}
        for group_name, rule_ids in CROSS_TOOL_GROUPS.items():
            for rid in rule_ids:
                rule_to_group[rid] = group_name

        def _get_tool_priority(f):
            return tool_priority.get(f.get("tool", ""), 0)

        # Pass 1: Exact dedup (same file + line + rule)
        seen_exact = {}
        for f in findings:
            file_path = f.get("file_path", f.get("file", ""))
            line = f.get("line_number", f.get("line", 0))
            rule = f.get("canonical_rule_id", f.get("rule_id", ""))
            key = (file_path, line, rule)

            if key not in seen_exact:
                seen_exact[key] = f
            elif _get_tool_priority(f) > _get_tool_priority(seen_exact[key]):
                seen_exact[key] = f

        after_exact = list(seen_exact.values())

        # Pass 2: Cross-tool dedup (same file + line + same category group)
        seen_cross = {}
        final = []
        for f in after_exact:
            file_path = f.get("file_path", f.get("file", ""))
            line = f.get("line_number", f.get("line", 0))
            rule = f.get("canonical_rule_id", f.get("rule_id", ""))
            group = rule_to_group.get(rule)

            if group:
                cross_key = (file_path, line, group)
                if cross_key not in seen_cross:
                    seen_cross[cross_key] = f
                elif _get_tool_priority(f) > _get_tool_priority(seen_cross[cross_key]):
                    seen_cross[cross_key] = f
                # Skip — will add from seen_cross later
            else:
                final.append(f)

        final.extend(seen_cross.values())

        removed = len(findings) - len(final)
        if removed:
            logger.info(f"      - Dedup: removed {removed} duplicate findings")
        return final

    def _cap_per_rule(self, findings, max_per_rule=5):
        """Cap findings per rule ID to prevent a single noisy rule from flooding results."""
        rule_counts = {}
        capped = []
        removed = 0

        for f in findings:
            rule = f.get("canonical_rule_id", f.get("rule_id", ""))
            rule_counts[rule] = rule_counts.get(rule, 0) + 1
            if rule_counts[rule] <= max_per_rule:
                capped.append(f)
            else:
                removed += 1

        if removed:
            logger.info(f"      - Per-rule cap: removed {removed} excess findings (max {max_per_rule}/rule)")
        return capped

    def _sort_by_priority(self, findings):
        """Sort findings so high-severity and security findings come first.
        This ensures they get AI explanations within the explanation limit."""
        severity_order = {"high": 0, "medium": 1, "low": 2}
        category_order = {"security": 0, "design": 1, "best-practice": 2, "dead-code": 3, "style": 4, "duplication": 5}

        def sort_key(f):
            sev = f.get("canonical_severity", f.get("severity", "low")).lower()
            cat = f.get("category", "style").lower()
            return (severity_order.get(sev, 3), category_order.get(cat, 6))

        return sorted(findings, key=sort_key)

    def run_js(self, repo_name="local", pr_number=None, limit=None, rich_output=False) -> int | None:
        """
        Run the full JS/TS analysis pipeline through AnalysisPipeline.
        Mirrors run() but uses JavaScriptAdapter instead of shell-based Python tools.
        Goes through the same pipeline steps: extra scanners, config filters,
        dedup, cap, sort, AI explanations, quality gate.
        """
        import dataclasses

        from CORE.adapters.js_adapter import JavaScriptAdapter

        logger.info(f"\n🟨 ACR-QA JS/TS Adapter — analyzing {self.target_dir}")
        logger.info("=" * 50)

        # Step 0: Rate limit
        import os

        from CORE.utils.rate_limiter import get_rate_limiter

        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        rate_limiter = get_rate_limiter(redis_host=redis_host, redis_port=redis_port)
        allowed, retry_after = rate_limiter.check_rate_limit(repo_name, pr_number)
        if not allowed:
            logger.error(f"      ✗ RATE LIMITED — retry after {retry_after:.1f}s")
            return None

        # Step 1: Create analysis run
        run_id = self.db.create_analysis_run(repo_name=repo_name, pr_number=pr_number)
        logger.info(f"\n[1/5] Created database run ID: {run_id}")

        # Step 2: Run JS tools
        logger.info("\n[2/5] Running JS/TS detection tools...")
        js_adapter = JavaScriptAdapter(target_dir=self.target_dir)
        results = js_adapter.run_tools()
        findings_obj = js_adapter.get_all_findings(results)

        # Convert to dicts and set canonical field aliases
        findings = [dataclasses.asdict(f) if hasattr(f, "__dataclass_fields__") else vars(f) for f in findings_obj]
        for f in findings:
            f.setdefault("canonical_rule_id", f.get("rule_id", "UNKNOWN"))
            f.setdefault("canonical_severity", f.get("severity", "low"))
            f.setdefault("file_path", f.get("file", ""))
            f.setdefault("line_number", f.get("line", 0))

        logger.info(f"      ✓ {len(findings)} raw findings from JS tools")

        # Step 2b: Extra scanners (CBoM — secrets/SCA not applicable for JS targets)
        logger.info("\n[2b/5] Running extra scanners...")
        try:
            from CORE.engines.cbom_scanner import CBoMScanner

            cbom = CBoMScanner(target_dir=str(self.target_dir))
            cbom_report = cbom.scan()
            cbom_findings = cbom.to_findings(cbom_report)
            findings.extend(cbom_findings)
            logger.info(
                f"      - CBoM: {cbom_report.total_usages} crypto usages — "
                f"🔴{cbom_report.unsafe_count} unsafe  "
                f"🟡{cbom_report.warn_count} warn  "
                f"🟢{cbom_report.safe_count} safe"
            )
        except Exception as e:
            logger.error(f"      - CBoM scan error: {e}")

        # Dependency reachability enrichment
        try:
            from CORE.engines.dependency_reachability import DependencyReachabilityChecker

            checker = DependencyReachabilityChecker(str(self.target_dir))
            findings = checker.enrich_findings(findings)
            # Count how many npm findings got reachability data
            enriched = [f for f in findings if "reachability_level" in f]
            if enriched:
                direct = sum(1 for f in enriched if f.get("reachability_level") == "DIRECT")
                transitive = sum(1 for f in enriched if f.get("reachability_level") == "TRANSITIVE")
                unknown = sum(1 for f in enriched if f.get("reachability_level") == "UNKNOWN")
                logger.info(
                    f"      - Reachability: {len(enriched)} npm findings — "
                    f"🔴{direct} direct  🟡{transitive} transitive  ⚪{unknown} unknown"
                )
        except Exception as e:
            logger.error(f"      - Reachability check error: {e}")

        # Step 3: Apply same pipeline filters as Python path
        logger.info("\n[3/5] Filtering and normalizing findings...")
        findings = self._apply_config_filters(findings)

        # Triage Memory: suppress findings that match learned FP rules (Feature 6)
        from CORE.engines.triage_memory import TriageMemory

        findings, suppressed = TriageMemory().suppress_findings(findings, self.db)
        if suppressed:
            logger.info(f"      - Triage Memory: suppressed {suppressed} known false positive(s)")

        findings = self._deduplicate_findings(findings)
        findings = self._sort_by_priority(findings)
        total_findings = len(findings)
        logger.info(f"      ✓ {total_findings} issues after filtering & dedup")

        # Step 4: AI explanations
        logger.info("\n[4/5] Generating AI explanations (Groq API)...")
        redis_client = rate_limiter.redis if rate_limiter and rate_limiter.redis else None
        self.explainer = ExplanationEngine(redis_client=redis_client)

        max_explanations = self.config.get("ai", {}).get("max_explanations", 50)
        effective_limit = min(limit, max_explanations) if limit else max_explanations
        # For JS: only explain HIGH findings by default to keep latency low
        high_findings = [f for f in findings if f.get("canonical_severity") == "high"]
        findings_to_explain = high_findings[:effective_limit] if effective_limit else high_findings

        findings_with_snippets = []
        for f in findings:
            f["_db_id"] = self.db.insert_finding(run_id, f)
            if f in findings_to_explain:
                snippet = extract_code_snippet(
                    f.get("file_path", f.get("file", "")),
                    f.get("line", 0),
                    context_lines=3,
                )
                findings_with_snippets.append({"finding": f, "snippet": snippet})

        if findings_with_snippets:
            logger.info(f"      Batching {len(findings_with_snippets)} HIGH explanations...")
            import time as _time

            start_time = _time.time()
            explanations = self.explainer.generate_explanation_batch(findings_with_snippets)
            total_time = int((_time.time() - start_time) * 1000)
            logger.info(f"✓ ({total_time}ms total)")
            for f_data, expl in zip(findings_with_snippets, explanations, strict=False):
                f = f_data["finding"]
                rule_id = f.get("canonical_rule_id", "UNKNOWN")
                if isinstance(expl, Exception):
                    logger.error(f"      ✗ {rule_id}: {expl}")
                else:
                    self.db.insert_explanation(f["_db_id"], expl)
        else:
            logger.info("      (no HIGH findings to explain)")

        # Mark run complete
        self.db.complete_analysis_run(run_id, total_findings)

        # Save run ID for GitHub Actions
        try:
            with open("/tmp/acr_run_id.txt", "w") as fh:
                fh.write(str(run_id))
        except OSError:
            pass

        # Step 5: Quality gate
        logger.info("\n[5/5] Quality Gate evaluation...")
        gate = QualityGate(config=self.config)
        gate_result = gate.evaluate(findings)

        if rich_output:
            self._print_rich_output(findings, gate_result, run_id, len(findings_with_snippets))
        else:
            gate.print_report(gate_result)
            logger.info(f"\n   Run ID: {run_id}")
            logger.info(f"   Explanations Generated: {len(findings_with_snippets)}")
            logger.info("\nNext Steps:")
            logger.info("   View dashboard: python3 FRONTEND/app.py")
            logger.info(f"   Generate report: python3 scripts/generate_report.py {run_id}")

        # Feature 9: Cross-language correlation
        try:
            from CORE.engines.cross_language_correlator import CrossLanguageCorrelator

            correlator = CrossLanguageCorrelator(str(self.target_dir))
            findings, corr_groups = correlator.enrich_findings(findings)
            if corr_groups:
                logger.info(f"\n[+] Cross-language correlations: {len(corr_groups)} chain(s) detected")
                for g in corr_groups:
                    logger.info(f"    [{g.combined_severity.upper()}] {g.correlation_type}: {g.chain_description[:80]}")

                # Save correlation results to the database
                for f in findings:
                    if "_db_id" in f and "correlation_chain" in f:
                        evidence = f.get("evidence", {})
                        if isinstance(evidence, str):
                            import json

                            try:
                                evidence = json.loads(evidence)
                            except Exception:
                                evidence = {}
                        evidence["correlation_chain"] = f["correlation_chain"]
                        evidence["correlation_severity"] = f.get("correlation_severity", "high")

                        self.db.update_finding_correlation(
                            finding_id=f["_db_id"], confidence_score=f.get("confidence_score"), evidence=evidence
                        )
        except Exception as e:
            logger.error(f"Cross-language correlation error: {e}")

        self._gate_passed = not gate.should_block(gate_result)
        self._gate_comment = gate.format_gate_comment(gate_result)

        # Print summary
        high = sum(1 for f in findings if f.get("canonical_severity") == "high")
        med = sum(1 for f in findings if f.get("canonical_severity") == "medium")
        low = sum(1 for f in findings if f.get("canonical_severity") == "low")
        logger.info(f"\n  Total findings: {total_findings}")
        logger.info(f"  🔴 High: {high}  🟡 Medium: {med}  🟢 Low: {low}")
        for err in results.get("errors", []):
            logger.info(f"  ⚠️  {err}")

        return run_id
        """Run autofix engine on findings and display diffs."""
        from CORE.engines.autofix import AutoFixEngine

        engine = AutoFixEngine()
        fixable = [f for f in findings if engine.can_fix(f.get("canonical_rule_id", ""))]
        if not fixable:
            logger.info("\n⚙️  No auto-fixable issues found.")
            return []

        logger.info(f"\n⚙️  Auto-Fix: {len(fixable)} fixable issues found")
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
                    logger.info(f"   ✓ {rule_id} @ {filepath}:{line} (confidence: {confidence})")
            except Exception as e:
                logger.error(f"   ✗ {rule_id} @ {filepath}:{line} — {e}")

        if results:
            logger.info(f"\n   📋 {len(results)} fixes generated. Review diffs above.")
        return results

    def run_extra_scanners(self, target_dir):
        """Run secrets detection, SCA scanning, and CBoM as part of the pipeline."""
        extra_findings = []

        try:
            from CORE.engines.secrets_detector import SecretsDetector

            logger.info("      - Secrets Detector (hardcoded credentials)")
            detector = SecretsDetector()
            results = detector.scan_directory(target_dir)
            if results.get("findings"):
                canonical = detector.to_canonical_findings(results["findings"])
                extra_findings.extend(canonical)
                logger.info(f"        → {len(results['findings'])} secrets found")
            else:
                logger.info("        → Clean (no secrets)")
        except Exception as e:
            logger.error(f"        ✗ Secrets scan error: {e}")

        try:
            from CORE.engines.sca_scanner import SCAScanner

            logger.info("      - SCA Scanner (dependency vulnerabilities)")
            scanner = SCAScanner(project_dir=target_dir)
            results = scanner.scan()
            if results.get("vulnerabilities"):
                extra_findings.extend(results.get("findings", []))
                logger.info(f"        → {len(results['vulnerabilities'])} vulnerabilities found")
            else:
                logger.info("        → Clean (no known vulnerabilities)")
        except Exception as e:
            logger.error(f"        ✗ SCA scan error: {e}")

        try:
            from CORE.engines.cbom_scanner import CBoMScanner

            logger.info("      - CBoM Scanner (cryptographic bill of materials)")
            cbom = CBoMScanner(target_dir=target_dir)
            report = cbom.scan()
            cbom_findings = cbom.to_findings(report)
            extra_findings.extend(cbom_findings)
            unsafe = report.unsafe_count
            warn = report.warn_count
            safe = report.safe_count
            algos = ", ".join(f"{k}×{v}" for k, v in report.algorithms_found.items()) or "none"
            logger.info(
                f"        → {report.total_usages} crypto usages: 🔴{unsafe} unsafe  🟡{warn} warn  🟢{safe} safe"
            )
            logger.info(f"        → Algorithms: {algos}")
        except Exception as e:
            logger.error(f"        ✗ CBoM scan error: {e}")

        return extra_findings

    def _load_findings(self):
        from CORE.engines.normalizer import normalize_all

        logger.info("      - Normalizing tool outputs...")
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
        logger.info("⚠️ Could not get git diff. Analyzing full directory instead.")
        return []


def main():
    parser = argparse.ArgumentParser(
        description="ACR-QA v3.2.4 Analysis Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""examples:
  python -m CORE --target-dir ./myproject
  python -m CORE --target-dir ./myproject --limit 0 --no-ai
  python -m CORE --target-dir ./myproject --json > results.json
  python -m CORE --target-dir ./myproject --rich --auto-fix""",
    )
    parser.add_argument("--target-dir", default="samples/realistic-issues", help="Directory to analyze")
    parser.add_argument("--repo-name", default="local", help="Repository name")
    parser.add_argument("--pr-number", type=int, help="Pull request number")
    parser.add_argument("--limit", type=int, default=None, help="Limit explanations (for speed)")
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
        "--baseline",
        type=int,
        dest="baseline_run_id",
        help="Baseline Run ID to compare against and mark new findings",
    )
    parser.add_argument(
        "--auto-fix",
        action="store_true",
        help="Generate auto-fix suggestions for fixable issues",
    )
    parser.add_argument(
        "--rich",
        action="store_true",
        help="Use Rich library for beautiful terminal output (tables, colors, panels)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="ACR-QA v3.2.4",
        help="Show program's version number and exit.",
    )
    parser.add_argument(
        "--no-ai",
        action="store_false",
        dest="ai",
        help="Skip AI explanation step (faster; useful for CI or large repos)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose DEBUG logging",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Enable quiet WARNING logging",
    )
    parser.add_argument(
        "--ai",
        action="store_true",
        dest="ai",
        default=True,
        help="Force AI explanation step",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output findings as JSON to stdout (pipe-friendly, for JS consumers)",
    )

    parser.add_argument(
        "--lang",
        choices=["auto", "python", "javascript", "typescript", "go"],
        default="auto",
        dest="language",
        help=(
            "Language to analyze: 'auto' detects from project files (default), "
            "'python', 'javascript'/'typescript' (alias: js/ts support)"
        ),
    )

    args = parser.parse_args()
    setup_logging(args.verbose, args.quiet)

    # Determine files to analyze
    files = None
    if args.diff_only:
        files = get_diff_files(args.diff_base)
        if files:
            logger.info(f"📝 Diff-only mode: {len(files)} changed Python files")
            for f in files:
                logger.info(f"   • {f}")
        else:
            logger.info("📝 No changed Python files found. Running full analysis.")

    pipeline = AnalysisPipeline(target_dir=args.target_dir, files=files)

    # --lang: Route to JS adapter when JS/TS project is detected or specified
    language = args.language
    if language == "auto":
        from CORE.adapters.js_adapter import JavaScriptAdapter

        language = JavaScriptAdapter.detect_language(args.target_dir)
        if language == "unknown":
            from CORE.adapters.go_adapter import GoAdapter

            if GoAdapter.detect_language(args.target_dir) == "go":
                language = "go"
        if language != "python":
            logger.info(f"🔍 Auto-detected language: {language}")

    if language == "go":
        import dataclasses

        from CORE.adapters.go_adapter import GoAdapter

        logger.info(f"\n🟦 ACR-QA Go Adapter — analyzing {args.target_dir}")
        logger.info("=" * 50)
        go_adapter = GoAdapter(target_dir=args.target_dir)
        tools_ok = go_adapter.check_tools_available()
        logger.info(
            f"      gosec: {'✓' if tools_ok['gosec'] else '✗'}  staticcheck: {'✓' if tools_ok['staticcheck'] else '✗'}"
        )
        results = go_adapter.run_tools()
        for err in results.get("errors", []):
            logger.info(f"      ⚠ {err}")
        findings_obj = go_adapter.get_all_findings(results)
        findings = [dataclasses.asdict(f) if hasattr(f, "__dataclass_fields__") else vars(f) for f in findings_obj]
        for f in findings:
            f.setdefault("canonical_rule_id", f.get("rule_id", "UNKNOWN"))
            f.setdefault("canonical_severity", f.get("severity", "low"))
            f.setdefault("file_path", f.get("file", ""))
            f.setdefault("line_number", f.get("line", 0))
        logger.info(f"      ✓ {len(findings)} findings from Go tools")
        # Print findings summary
        high = [f for f in findings if f.get("canonical_severity") == "high"]
        medium = [f for f in findings if f.get("canonical_severity") == "medium"]
        low = [f for f in findings if f.get("canonical_severity") == "low"]
        logger.info(f"\n  🔴 High: {len(high)}  🟡 Medium: {len(medium)}  🟢 Low: {len(low)}")
        logger.info("\n  Top findings:")
        for f in sorted(
            findings, key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x.get("canonical_severity", "low"), 2)
        )[:10]:
            logger.info(
                f"    [{f.get('canonical_severity','?').upper()}] {f.get('canonical_rule_id')} — {f.get('file_path','').split('/')[-1]}:{f.get('line_number',0)} — {f.get('message','')[:60]}"
            )
        return

    if language in ("javascript", "typescript"):
        run_id = pipeline.run_js(
            repo_name=args.repo_name,
            pr_number=args.pr_number,
            limit=args.limit if args.ai else 0,
            rich_output=args.rich,
        )
        if args.json_output and run_id:
            findings_path = Path("DATA/outputs/findings.json")
            if findings_path.exists():
                with open(findings_path) as fp:
                    logger.info(fp.read())
            else:
                logger.info("[]")
        if run_id and hasattr(pipeline, "_gate_passed") and not pipeline._gate_passed:
            logger.error("\n❌ Exiting with code 1 (quality gate failed)")
            sys.exit(1)
        return

    # --no-ai: override limit to 0 to skip AI explanation step entirely
    effective_limit = 0 if not args.ai else args.limit

    run_id = pipeline.run(
        repo_name=args.repo_name,
        pr_number=args.pr_number,
        limit=effective_limit,
        files=files,
        rich_output=args.rich,
        baseline_run_id=args.baseline_run_id,
    )

    # --json: dump findings as JSON to stdout (pipe-friendly, for JS consumers)
    if args.json_output:
        findings_path = Path("DATA/outputs/findings.json")
        if findings_path.exists():
            with open(findings_path) as fp:
                logger.info(fp.read())
        else:
            logger.info("[]")

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
        logger.error("\n❌ Exiting with code 1 (quality gate failed)")
        sys.exit(1)


if __name__ == "__main__":
    main()
