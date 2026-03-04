#!/usr/bin/env python3
"""
OWASP Top 10 and SANS Top 25 Compliance Checker
Maps ACR-QA findings to industry security standards
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from DATABASE.database import Database

# OWASP Top 10 2021 Mapping
OWASP_TOP_10 = {
    "A01:2021-Broken Access Control": ["SECURITY-004", "SECURITY-019"],
    "A02:2021-Cryptographic Failures": [
        "SECURITY-009",
        "SECURITY-010",
        "SECURITY-014",
        "SECURITY-015",
        "SECURITY-016",
        "SECURITY-017",
    ],
    "A03:2021-Injection": [
        "SECURITY-001",
        "SECURITY-021",
        "SECURITY-027",
        "SECURITY-028",
    ],
    "A04:2021-Insecure Design": ["PATTERN-001", "SOLID-001", "COMPLEXITY-001"],
    "A05:2021-Security Misconfiguration": [
        "SECURITY-003",
        "SECURITY-006",
        "SECURITY-013",
    ],
    "A06:2021-Vulnerable Components": ["SECURITY-008", "SECURITY-018"],
    "A07:2021-Authentication Failures": ["SECURITY-005", "HARDCODE-001"],
    "A08:2021-Software and Data Integrity": [
        "SECURITY-002",
        "SECURITY-012",
        "SECURITY-033",
    ],
    "A09:2021-Logging Failures": ["SECURITY-007"],
    "A10:2021-SSRF": [
        "SECURITY-020",
        "SECURITY-022",
        "SECURITY-023",
        "SECURITY-024",
        "SECURITY-025",
        "SECURITY-026",
    ],
}

# SANS Top 25 CWE Mapping (subset)
SANS_TOP_25 = {
    "CWE-79: XSS": ["SECURITY-012", "SECURITY-031", "SECURITY-032", "SECURITY-033"],
    "CWE-89: SQL Injection": ["SECURITY-027", "SECURITY-029", "SECURITY-030"],
    "CWE-78: OS Command Injection": ["SECURITY-021", "SECURITY-028"],
    "CWE-20: Input Validation": ["SECURITY-001"],
    "CWE-125: Out-of-bounds Read": ["COMPLEXITY-001"],
    "CWE-22: Path Traversal": ["SECURITY-026"],
    "CWE-352: CSRF": ["SECURITY-013"],
    "CWE-434: File Upload": ["SECURITY-003"],
    "CWE-306: Missing Authentication": ["SECURITY-005", "HARDCODE-001"],
    "CWE-502: Deserialization": ["SECURITY-008", "SECURITY-018"],
}


def generate_compliance_report(run_id=None):
    """Generate OWASP and SANS compliance report"""
    db = Database()

    # Get findings
    if run_id:
        findings = db.get_findings_with_explanations(run_id)
    else:
        runs = db.get_recent_runs(limit=1)
        if not runs:
            print("❌ No analysis runs found")
            return
        findings = db.get_findings_with_explanations(runs[0]["id"])
        run_id = runs[0]["id"]

    # Count findings by canonical rule
    rule_counts = {}
    for f in findings:
        rule_id = f.get("canonical_rule_id", f.get("rule_id"))
        rule_counts[rule_id] = rule_counts.get(rule_id, 0) + 1

    print(f"\n{'='*60}")
    print(f"🔒 Security Compliance Report - Run {run_id}")
    print(f"{'='*60}\n")

    # OWASP Top 10 Analysis
    print("📊 OWASP Top 10:2021 Coverage\n")
    owasp_total = 0
    for category, rules in OWASP_TOP_10.items():
        count = sum(rule_counts.get(rule, 0) for rule in rules)
        if count > 0:
            status = "🔴" if count > 5 else "🟡" if count > 0 else "🟢"
            print(f"{status} {category}: {count} issue(s)")
            owasp_total += count

    print(f"\n   Total OWASP-related issues: {owasp_total}")

    # SANS Top 25 Analysis
    print(f"\n{'='*60}")
    print("📊 SANS Top 25 CWE Coverage\n")
    sans_total = 0
    for cwe, rules in SANS_TOP_25.items():
        count = sum(rule_counts.get(rule, 0) for rule in rules)
        if count > 0:
            status = "🔴" if count > 5 else "🟡" if count > 0 else "🟢"
            print(f"{status} {cwe}: {count} issue(s)")
            sans_total += count

    print(f"\n   Total SANS-related issues: {sans_total}")

    # Compliance Score — Weighted by Severity
    print(f"\n{'='*60}")

    # Severity-weighted scoring: high = -5, medium = -2, low = -1
    severity_weights = {"high": 5, "medium": 2, "low": 1}
    weighted_deductions = 0
    severity_counts = {"high": 0, "medium": 0, "low": 0}

    for f in findings:
        if f.get("category") == "security":
            sev = f.get("canonical_severity", "medium").lower()
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
            weighted_deductions += severity_weights.get(sev, 2)

    total_security = sum(severity_counts.values())

    # Score: start at 100, deduct weighted points, floor at 0
    compliance_score = max(0, 100 - weighted_deductions)

    # OWASP and SANS coverage
    owasp_categories_hit = len([c for c, r in OWASP_TOP_10.items() if any(rule_counts.get(rule, 0) > 0 for rule in r)])
    sans_categories_hit = len([c for c, r in SANS_TOP_25.items() if any(rule_counts.get(rule, 0) > 0 for rule in r)])
    owasp_coverage_pct = round((owasp_categories_hit / 10) * 100, 1)
    sans_coverage_pct = round((sans_categories_hit / 10) * 100, 1)

    # Letter grade
    if compliance_score >= 90:
        grade = "A"
    elif compliance_score >= 80:
        grade = "B"
    elif compliance_score >= 70:
        grade = "C"
    elif compliance_score >= 60:
        grade = "D"
    else:
        grade = "F"

    print(f"🎯 Compliance Score: {compliance_score}/100 (Grade: {grade})")
    print("   Scoring: High=-5pts, Medium=-2pts, Low=-1pt per issue")
    print(f"   High severity:   {severity_counts.get('high', 0)} issues (-{severity_counts.get('high', 0) * 5} pts)")
    print(
        f"   Medium severity: {severity_counts.get('medium', 0)} issues (-{severity_counts.get('medium', 0) * 2} pts)"
    )
    print(f"   Low severity:    {severity_counts.get('low', 0)} issues (-{severity_counts.get('low', 0) * 1} pts)")
    print(f"   Total Security Issues: {total_security}")
    print(f"   OWASP Coverage: {owasp_categories_hit}/10 ({owasp_coverage_pct}%)")
    print(f"   SANS Coverage:  {sans_categories_hit}/10 ({sans_coverage_pct}%)")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate compliance report")
    parser.add_argument("--run-id", type=int, help="Analysis run ID (default: latest)")
    args = parser.parse_args()

    generate_compliance_report(args.run_id)
