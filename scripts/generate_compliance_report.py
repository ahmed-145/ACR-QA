#!/usr/bin/env python3
"""
ACR-QA OWASP Top 10 & CWE/SANS Top 25 Compliance Report Generator
Maps security findings to OWASP Top 10 (2021) and CWE IDs for regulatory compliance.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse

from CORE import __version__
from DATABASE.database import Database

# ─── OWASP Top 10 (2021) Mapping ──────────────────────────────────────────
OWASP_TOP_10 = {
    "A01": {
        "name": "Broken Access Control",
        "description": "Restrictions on authenticated users are not properly enforced.",
        "cwe_ids": ["CWE-200", "CWE-284", "CWE-285", "CWE-352", "CWE-639"],
        "rule_ids": ["PATH-001", "INPUT-001"],
    },
    "A02": {
        "name": "Cryptographic Failures",
        "description": "Failures related to cryptography leading to exposure of sensitive data.",
        "cwe_ids": ["CWE-259", "CWE-327", "CWE-328", "CWE-330", "CWE-331"],
        "rule_ids": ["HARDCODE-001", "SECURITY-005"],
    },
    "A03": {
        "name": "Injection",
        "description": "User-supplied data is not validated, filtered, or sanitized.",
        "cwe_ids": ["CWE-20", "CWE-77", "CWE-78", "CWE-79", "CWE-89", "CWE-94"],
        "rule_ids": ["SECURITY-001", "SECURITY-021", "SECURITY-027"],
    },
    "A04": {
        "name": "Insecure Design",
        "description": "Missing or ineffective control design.",
        "cwe_ids": ["CWE-209", "CWE-256", "CWE-501", "CWE-522"],
        "rule_ids": ["PATTERN-001", "GLOBAL-001", "RETURN-001"],
    },
    "A05": {
        "name": "Security Misconfiguration",
        "description": "Missing security hardening or improperly configured permissions.",
        "cwe_ids": ["CWE-16", "CWE-611", "CWE-614"],
        "rule_ids": ["SECURITY-003", "SECURITY-004", "SECURITY-006"],
    },
    "A06": {
        "name": "Vulnerable and Outdated Components",
        "description": "Using components with known vulnerabilities.",
        "cwe_ids": ["CWE-1104"],
        "rule_ids": [],  # Mapped via SCA scanner findings
    },
    "A07": {
        "name": "Identification and Authentication Failures",
        "description": "Confirmation of the user's identity and session management issues.",
        "cwe_ids": ["CWE-287", "CWE-384"],
        "rule_ids": [],
    },
    "A08": {
        "name": "Software and Data Integrity Failures",
        "description": "Code and infrastructure that does not protect against integrity violations.",
        "cwe_ids": ["CWE-502", "CWE-829"],
        "rule_ids": ["SECURITY-008"],
    },
    "A09": {
        "name": "Security Logging and Monitoring Failures",
        "description": "Insufficient logging, detection, monitoring, and active response.",
        "cwe_ids": ["CWE-117", "CWE-223", "CWE-532", "CWE-778"],
        "rule_ids": ["LOG-001", "ERROR-001", "SECURITY-007"],
    },
    "A10": {
        "name": "Server-Side Request Forgery (SSRF)",
        "description": "Fetching a remote resource without validating the user-supplied URL.",
        "cwe_ids": ["CWE-918"],
        "rule_ids": [],
    },
}

# ─── CWE Mapping for ACR-QA Rules ─────────────────────────────────────────
RULE_TO_CWE = {
    "SECURITY-001": "CWE-94",  # Code Injection (eval)
    "SECURITY-002": "CWE-617",  # Assert (reachable assertion)
    "SECURITY-003": "CWE-732",  # Incorrect Permission Assignment
    "SECURITY-004": "CWE-200",  # Exposure of Sensitive Information
    "SECURITY-005": "CWE-259",  # Use of Hard-coded Password
    "SECURITY-006": "CWE-377",  # Insecure Temporary File
    "SECURITY-007": "CWE-390",  # Detection of Error without Action
    "SECURITY-008": "CWE-502",  # Deserialization of Untrusted Data
    "SECURITY-021": "CWE-78",  # OS Command Injection
    "SECURITY-027": "CWE-89",  # SQL Injection
    "HARDCODE-001": "CWE-798",  # Use of Hard-coded Credentials
    "PATH-001": "CWE-22",  # Path Traversal
    "REGEX-001": "CWE-1333",  # ReDoS
    "INPUT-001": "CWE-20",  # Improper Input Validation
    "LOG-001": "CWE-532",  # Information Exposure Through Logs
    "THREAD-001": "CWE-362",  # Race Condition
    "EXCEPT-001": "CWE-396",  # Catching Overly Broad Exceptions
    "ERROR-001": "CWE-390",  # Detection of Error without Action
    "ASSERT-001": "CWE-617",  # Reachable Assertion
}


def generate_compliance_report(run_id=None, output_format="md"):
    """
    Generate OWASP Top 10 compliance report from analysis findings.

    Args:
        run_id: Analysis run ID (None = latest)
        output_format: 'md' for markdown, 'json' for JSON

    Returns:
        Report string (markdown or JSON)
    """
    db = Database()

    # Get run
    if not run_id:
        runs = db.get_recent_runs(limit=1)
        if not runs:
            return "❌ No analysis runs found."
        run_id = runs[0]["id"]

    findings = db.get_findings(run_id)
    if not findings:
        return f"⚠️  No findings for run {run_id}"

    # Filter to security-relevant findings
    security_findings = [
        f for f in findings if f.get("category") == "security" or f.get("canonical_rule_id", "") in RULE_TO_CWE
    ]

    # Map findings to OWASP categories
    owasp_results = {}
    unmapped_findings = []

    for owasp_id, owasp_info in OWASP_TOP_10.items():
        matched = [
            f
            for f in security_findings
            if f.get("canonical_rule_id") in owasp_info["rule_ids"] or f.get("rule_id") in owasp_info["rule_ids"]
        ]
        owasp_results[owasp_id] = {
            "name": owasp_info["name"],
            "description": owasp_info["description"],
            "cwe_ids": owasp_info["cwe_ids"],
            "status": "FAIL" if matched else "PASS",
            "finding_count": len(matched),
            "findings": matched,
        }

    # Find unmapped security findings
    mapped_rule_ids = set()
    for info in OWASP_TOP_10.values():
        mapped_rule_ids.update(info["rule_ids"])

    unmapped_findings = [
        f
        for f in security_findings
        if f.get("canonical_rule_id") not in mapped_rule_ids and f.get("rule_id") not in mapped_rule_ids
    ]

    if output_format == "json":
        import json

        return json.dumps(
            {
                "run_id": run_id,
                "version": __version__,
                "total_findings": len(findings),
                "security_findings": len(security_findings),
                "owasp_results": {
                    k: {
                        "name": v["name"],
                        "status": v["status"],
                        "finding_count": v["finding_count"],
                        "cwe_ids": v["cwe_ids"],
                    }
                    for k, v in owasp_results.items()
                },
                "unmapped_security_findings": len(unmapped_findings),
            },
            indent=2,
        )

    # Generate markdown report
    return _build_markdown_report(run_id, findings, security_findings, owasp_results, unmapped_findings)


def _build_markdown_report(run_id, findings, security_findings, owasp_results, unmapped_findings):
    """Build the markdown compliance report."""
    total = len(findings)
    sec_total = len(security_findings)
    pass_count = sum(1 for r in owasp_results.values() if r["status"] == "PASS")
    fail_count = sum(1 for r in owasp_results.values() if r["status"] == "FAIL")

    report = f"""# 🛡️ ACR-QA OWASP Top 10 Compliance Report

**Run ID:** {run_id}
**Generated by:** ACR-QA v{__version__}
**Standard:** OWASP Top 10 (2021)

---

## 📊 Executive Summary

| Metric | Value |
|--------|-------|
| **Total Findings** | {total} |
| **Security Findings** | {sec_total} |
| **OWASP Categories Passed** | {pass_count}/10 |
| **OWASP Categories Failed** | {fail_count}/10 |
| **Compliance Rate** | {pass_count * 10}% |

"""

    # Overall status
    if fail_count == 0:
        report += "> ✅ **COMPLIANT** — No OWASP Top 10 violations detected.\n\n"
    elif fail_count <= 3:
        report += f"> ⚠️ **PARTIAL COMPLIANCE** — {fail_count} OWASP categories need attention.\n\n"
    else:
        report += f"> 🔴 **NON-COMPLIANT** — {fail_count} OWASP categories violated.\n\n"

    report += "---\n\n## 📋 OWASP Top 10 Breakdown\n\n"

    for owasp_id, result in owasp_results.items():
        status_icon = "✅" if result["status"] == "PASS" else "🔴"
        report += f"### {status_icon} {owasp_id}: {result['name']}\n\n"
        report += f"*{result['description']}*\n\n"
        report += f"**Status:** {result['status']} | "
        report += f"**Findings:** {result['finding_count']} | "
        report += f"**CWEs:** {', '.join(result['cwe_ids'][:3])}\n\n"

        if result["findings"]:
            report += "| Rule | File | Line | Message |\n"
            report += "|------|------|------|---------|\n"
            for f in result["findings"][:5]:
                rule = f.get("canonical_rule_id", f.get("rule_id", "?"))
                filepath = Path(f.get("file_path", "?")).name
                line = f.get("line_number", "?")
                msg = f.get("message", "")[:60]
                cwe = RULE_TO_CWE.get(rule, "—")
                report += f"| {rule} ({cwe}) | `{filepath}` | {line} | {msg} |\n"
            if result["finding_count"] > 5:
                report += f"\n*... and {result['finding_count'] - 5} more*\n"
            report += "\n"

    # CWE Summary
    report += "---\n\n## 🔗 CWE Mapping Summary\n\n"
    report += "| ACR-QA Rule | CWE ID | Category |\n"
    report += "|-------------|--------|----------|\n"
    for rule_id, cwe_id in sorted(RULE_TO_CWE.items()):
        report += f"| {rule_id} | {cwe_id} | Security |\n"

    # Unmapped findings
    if unmapped_findings:
        report += f"\n---\n\n## ⚠️ Unmapped Security Findings ({len(unmapped_findings)})\n\n"
        report += "These security findings don't map to a specific OWASP category:\n\n"
        for f in unmapped_findings[:10]:
            rule = f.get("canonical_rule_id", f.get("rule_id", "?"))
            msg = f.get("message", "")[:80]
            report += f"- **{rule}**: {msg}\n"

    report += f"\n---\n\n*Generated by ACR-QA v{__version__}*\n"
    return report


def get_compliance_data(run_id=None):
    """
    Get compliance data as a dict (for Flask API endpoint).

    Returns:
        Dict with OWASP mapping, pass/fail status, and finding counts.
    """
    import json

    report_json = generate_compliance_report(run_id=run_id, output_format="json")
    return json.loads(report_json)


def main():
    parser = argparse.ArgumentParser(description="ACR-QA OWASP Top 10 Compliance Report")
    parser.add_argument("--run-id", type=int, help="Analysis run ID (default: latest)")
    parser.add_argument("--format", "-f", choices=["md", "json"], default="md", help="Output format (default: md)")
    parser.add_argument("--output", "-o", help="Output file path (default: stdout)")
    args = parser.parse_args()

    report = generate_compliance_report(run_id=args.run_id, output_format=args.format)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w") as f:
            f.write(report)
        print(f"✅ Compliance report saved to {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
