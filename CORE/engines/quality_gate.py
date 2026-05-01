#!/usr/bin/env python3
"""
ACR-QA Quality Gate Engine
Enforces configurable thresholds to pass/fail CI pipelines.
"""

import logging
from typing import Any

DEFAULT_THRESHOLDS = {
    "mode": "block",  # "block" = fail CI | "warn" = post comment only, allow merge
    "max_high": 0,  # Zero tolerance for high-severity findings (SQL injection, XSS, etc.)
    "max_medium": 20,  # Allow up to 20 medium issues (realistic for large codebases)
    "max_total": 200,  # Realistic cap for medium-sized codebases
    "max_security": 3,  # Allow up to 3 low-risk security findings (e.g., assert-for-validation)
    "min_confidence": 0,  # No minimum confidence requirement (0 = disabled)
}

logger = logging.getLogger(__name__)


class QualityGate:
    """
    Evaluate analysis results against configurable thresholds.

    Used by CI/CD to block merges when code quality drops below standards.
    Reads thresholds from .acrqa.yml quality_gate section.

    Example .acrqa.yml:
        quality_gate:
          max_high: 0
          max_medium: 5
          max_total: 50
          max_security: 0
    """

    def __init__(self, config: dict | None = None):
        self.thresholds = DEFAULT_THRESHOLDS.copy()
        if config and isinstance(config, dict):
            gate_config = config.get("quality_gate", {})
            if gate_config:
                self.thresholds.update(gate_config)

    def evaluate(self, findings: list[dict]) -> dict[str, Any]:
        """
        Evaluate findings against quality gate thresholds.

        Args:
            findings: List of canonical finding dicts

        Returns:
            Dict with:
                passed: bool
                summary: str
                details: list of check results
                counts: severity/category counts
        """
        # Count by severity
        counts = {"high": 0, "medium": 0, "low": 0, "total": len(findings)}
        category_counts: dict[str, int] = {}

        for f in findings:
            sev = f.get("canonical_severity", f.get("severity", "low")).lower()
            counts[sev] = counts.get(sev, 0) + 1

            cat = f.get("category", "unknown").lower()
            category_counts[cat] = category_counts.get(cat, 0) + 1

        # Run checks
        checks = []
        passed = True

        # Check: max high severity
        max_high = int(str(self.thresholds.get("max_high", 0)))
        high_ok = counts["high"] <= max_high
        checks.append(
            {
                "name": "High Severity",
                "passed": high_ok,
                "actual": counts["high"],
                "threshold": max_high,
                "message": f"{counts['high']} high-severity findings (max: {max_high})",
            }
        )
        if not high_ok:
            passed = False

        # Check: max medium severity
        max_medium = int(str(self.thresholds.get("max_medium", 10)))
        med_ok = counts["medium"] <= max_medium
        checks.append(
            {
                "name": "Medium Severity",
                "passed": med_ok,
                "actual": counts["medium"],
                "threshold": max_medium,
                "message": f"{counts['medium']} medium-severity findings (max: {max_medium})",
            }
        )
        if not med_ok:
            passed = False

        # Check: max total findings
        max_total = int(str(self.thresholds.get("max_total", 100)))
        total_ok = counts["total"] <= max_total
        checks.append(
            {
                "name": "Total Findings",
                "passed": total_ok,
                "actual": counts["total"],
                "threshold": max_total,
                "message": f"{counts['total']} total findings (max: {max_total})",
            }
        )
        if not total_ok:
            passed = False

        # Check: max security findings
        max_security = int(str(self.thresholds.get("max_security", 0)))
        security_count = category_counts.get("security", 0)
        sec_ok = security_count <= max_security
        checks.append(
            {
                "name": "Security Findings",
                "passed": sec_ok,
                "actual": security_count,
                "threshold": max_security,
                "message": f"{security_count} security findings (max: {max_security})",
            }
        )
        if not sec_ok:
            passed = False

        # Build summary
        status = "✅ PASSED" if passed else "❌ FAILED"
        failed_checks = [c for c in checks if not c["passed"]]

        return {
            "passed": passed,
            "status": status,
            "summary": f"Quality Gate {status}: {len(failed_checks)}/{len(checks)} checks failed"
            if not passed
            else f"Quality Gate {status}: all {len(checks)} checks passed",
            "checks": checks,
            "counts": counts,
            "category_counts": category_counts,
        }

    def should_block(self, result: dict) -> bool:
        """
        Return True if CI should exit 1 and block the merge.

        In 'warn' mode the gate always returns False (never blocks),
        even when thresholds are exceeded — findings are still posted
        as PR comments for visibility.

        In 'block' mode (default) returns True when gate failed.
        """
        mode = str(self.thresholds.get("mode", "block")).lower()
        if mode == "warn":
            return False
        return not result["passed"]

    def format_gate_comment(self, result: dict) -> str:
        """
        Format quality gate result as a GitHub PR comment (markdown).
        Posted as a top-level PR comment summarising the gate outcome.
        """
        mode = str(self.thresholds.get("mode", "block")).lower()
        mode_label = "🛑 BLOCKING" if mode == "block" else "⚠️ WARN-ONLY"
        counts = result["counts"]

        lines = [
            f"## 🚦 ACR-QA Quality Gate — {result['status']}",
            f"**Mode:** {mode_label}",
            "",
            "| Severity | Count |",
            "|----------|-------|",
            f"| 🔴 High   | {counts['high']} |",
            f"| 🟡 Medium | {counts['medium']} |",
            f"| 🟢 Low    | {counts['low']} |",
            f"| **Total** | **{counts['total']}** |",
            "",
            "### Checks",
        ]
        for check in result["checks"]:
            icon = "✅" if check["passed"] else "❌"
            lines.append(f"- {icon} {check['message']}")

        if not result["passed"]:
            if mode == "block":
                lines += ["", "---", "❌ **Merge blocked** — fix the findings above to proceed."]
            else:
                lines += ["", "---", "⚠️ **Warn-only mode** — merge is allowed but findings need attention."]
        else:
            lines += ["", "---", "✅ **All checks passed** — safe to merge."]

        return "\n".join(lines)

    def print_report(self, result: dict) -> None:
        """Print a formatted quality gate report to stdout."""
        logger.info("\n" + "═" * 50)
        logger.info(f"  🚦 Quality Gate: {result['status']}")
        logger.info("═" * 50)

        counts = result["counts"]
        logger.info(
            f"  Total: {counts['total']}  │  "
            f"🔴 High: {counts['high']}  │  "
            f"🟡 Medium: {counts['medium']}  │  "
            f"🟢 Low: {counts['low']}"
        )
        logger.info("─" * 50)

        for check in result["checks"]:
            icon = "✅" if check["passed"] else "❌"
            logger.info(f"  {icon} {check['name']}: {check['message']}")

        logger.info("═" * 50)


if __name__ == "__main__":
    # Demo
    sample_findings = [
        {
            "canonical_severity": "high",
            "category": "security",
            "canonical_rule_id": "SECURITY-027",
        },
        {
            "canonical_severity": "medium",
            "category": "design",
            "canonical_rule_id": "SOLID-001",
        },
        {
            "canonical_severity": "low",
            "category": "style",
            "canonical_rule_id": "IMPORT-001",
        },
        {
            "canonical_severity": "low",
            "category": "style",
            "canonical_rule_id": "VAR-001",
        },
    ]

    gate = QualityGate()
    result = gate.evaluate(sample_findings)
    gate.print_report(result)
