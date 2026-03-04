#!/usr/bin/env python3
"""
ACR-QA Quality Gate Engine
Enforces configurable thresholds to pass/fail CI pipelines.
"""

from typing import Any

DEFAULT_THRESHOLDS = {
    "max_high": 0,  # Zero tolerance for high-severity findings
    "max_medium": 10,  # Allow up to 10 medium issues
    "max_total": 100,  # Cap total findings
    "max_security": 0,  # Zero tolerance for security findings
    "min_confidence": 0,  # No minimum confidence requirement (0 = disabled)
}


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
        category_counts = {}

        for f in findings:
            sev = f.get("canonical_severity", f.get("severity", "low")).lower()
            counts[sev] = counts.get(sev, 0) + 1

            cat = f.get("category", "unknown").lower()
            category_counts[cat] = category_counts.get(cat, 0) + 1

        # Run checks
        checks = []
        passed = True

        # Check: max high severity
        max_high = self.thresholds.get("max_high", 0)
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
        max_medium = self.thresholds.get("max_medium", 10)
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
        max_total = self.thresholds.get("max_total", 100)
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
        max_security = self.thresholds.get("max_security", 0)
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

    def print_report(self, result: dict) -> None:
        """Print a formatted quality gate report to stdout."""
        print("\n" + "═" * 50)
        print(f"  🚦 Quality Gate: {result['status']}")
        print("═" * 50)

        counts = result["counts"]
        print(
            f"  Total: {counts['total']}  │  "
            f"🔴 High: {counts['high']}  │  "
            f"🟡 Medium: {counts['medium']}  │  "
            f"🟢 Low: {counts['low']}"
        )
        print("─" * 50)

        for check in result["checks"]:
            icon = "✅" if check["passed"] else "❌"
            print(f"  {icon} {check['name']}: {check['message']}")

        print("═" * 50)


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
