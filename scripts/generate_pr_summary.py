#!/usr/bin/env python3
"""
ACR-QA PR Summary Generator
Generates human-readable summaries for pull requests with risk scoring
"""

import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from DATABASE.database import Database


def calculate_risk_score(findings: list[dict]) -> dict[str, Any]:
    """
    Calculate a risk score (0-100) based on findings.

    Scoring weights:
    - Critical/High severity: 10 points each (max 50)
    - Security category: 5 bonus points each (max 25)
    - Medium severity: 3 points each (max 15)
    - Low severity: 1 point each (max 10)

    Returns:
        Dict with score, label, and breakdown
    """
    if not findings:
        return {"score": 0, "label": "✅ Clean", "color": "green", "breakdown": {}}

    high_count = sum(1 for f in findings if f.get("severity") in ("high", "critical"))
    medium_count = sum(1 for f in findings if f.get("severity") == "medium")
    low_count = sum(1 for f in findings if f.get("severity") == "low")
    security_count = sum(1 for f in findings if f.get("category") == "security")

    score = (
        min(50, high_count * 10)
        + min(25, security_count * 5)
        + min(15, medium_count * 3)
        + min(10, low_count * 1)
    )
    score = min(100, score)

    if score >= 70:
        label, color = "🔴 High Risk", "red"
    elif score >= 40:
        label, color = "🟡 Medium Risk", "yellow"
    elif score >= 10:
        label, color = "🟢 Low Risk", "green"
    else:
        label, color = "✅ Minimal Risk", "green"

    return {
        "score": score,
        "label": label,
        "color": color,
        "breakdown": {
            "high_severity": high_count,
            "medium_severity": medium_count,
            "low_severity": low_count,
            "security_issues": security_count,
        },
    }


def generate_pr_summary(run_id: int = None, findings: list[dict] = None) -> str:
    """
    Generate a markdown summary for a PR based on analysis findings.

    Args:
        run_id: Analysis run ID (uses latest if not provided)
        findings: Optional pre-loaded findings list (skips DB query)

    Returns:
        Markdown formatted summary
    """
    db = Database()

    # Get the run
    if run_id:
        runs = [r for r in db.get_recent_runs(limit=100) if r["id"] == run_id]
        if not runs:
            return f"❌ Run {run_id} not found"
        run = runs[0]
    else:
        runs = db.get_recent_runs(limit=1)
        if not runs:
            return "❌ No analysis runs found"
        run = runs[0]

    # Get findings for this run
    if findings is None:
        findings = db.get_findings(run["id"])

    # Calculate statistics
    total = len(findings)
    severity_counts = Counter(f.get("severity", "low") for f in findings)
    category_counts = Counter(f.get("category", "unknown") for f in findings)
    file_counts = Counter(f.get("file_path", "unknown") for f in findings)

    # Get top categories and files
    top_categories = category_counts.most_common(5)
    top_files = file_counts.most_common(5)

    # Critical findings
    critical_findings = [
        f for f in findings if f.get("severity") in ("high", "critical")
    ]

    # Risk score
    risk = calculate_risk_score(findings)

    # Build summary
    summary = f"""## 📊 ACR-QA Analysis Summary

**Repository:** {run.get('repo_name', 'Unknown')}  
**Run ID:** {run['id']}  
**Status:** {run.get('status', 'unknown')}  
**Risk Score:** {risk['label']} ({risk['score']}/100)

---

### 📈 Overview

| Metric | Value |
|--------|-------|
| **Total Issues** | {total} |
| **Critical/High** | {severity_counts.get('high', 0) + severity_counts.get('critical', 0)} |
| **Medium** | {severity_counts.get('medium', 0)} |
| **Low/Info** | {severity_counts.get('low', 0) + severity_counts.get('info', 0)} |
| **Risk Score** | {risk['score']}/100 |

---

### 🏷️ Issues by Category

"""

    for cat, count in top_categories:
        pct = (count / total * 100) if total > 0 else 0
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        summary += f"- **{cat}**: {count} ({pct:.0f}%) `{bar}`\n"

    summary += """
---

### 📁 Most Affected Files

"""

    for filepath, count in top_files:
        filename = Path(filepath).name if filepath else "unknown"
        summary += f"- `{filename}`: {count} issues\n"

    if critical_findings:
        summary += f"""
---

### 🚨 Critical Issues ({len(critical_findings)})

"""
        for f in critical_findings[:5]:  # Show top 5 critical
            rule_id = f.get("canonical_rule_id", "UNKNOWN")
            msg = f.get("message", "No message")[:80]
            filepath = f.get("file_path", "unknown")
            line = f.get("line_number", 0)
            summary += f"- **{rule_id}** in `{Path(filepath).name}:{line}` — {msg}\n"

        if len(critical_findings) > 5:
            summary += f"\n*...and {len(critical_findings) - 5} more critical issues*\n"

    # Auto-fixable count
    auto_fixable_rules = {
        "IMPORT-001",
        "VAR-001",
        "BOOL-001",
        "STRING-001",
        "TYPE-001",
        "EXCEPT-001",
    }
    auto_fixable = [
        f for f in findings if f.get("canonical_rule_id") in auto_fixable_rules
    ]

    summary += f"""
---

### ✅ Recommendations

1. Address **{len(critical_findings)} critical issues** first
2. Review files with most issues: {', '.join(f'`{Path(f).name}`' for f, _ in top_files[:2])}
3. **{len(auto_fixable)} issues** can be auto-fixed with `acr-qa --autofix`
4. Consider adding pre-commit hooks to catch issues early

---

*Generated by ACR-QA v2.0 | [View Full Report](dashboard)*
"""

    return summary


def generate_summary_from_findings(findings: list[dict]) -> str:
    """
    Generate a summary directly from a list of finding dicts (no DB required).
    Useful for inline PR comments.
    """
    total = len(findings)
    if total == 0:
        return "✅ **No issues found!** This PR looks clean."

    risk = calculate_risk_score(findings)
    severity_counts = Counter(f.get("severity", "low") for f in findings)
    high = severity_counts.get("high", 0) + severity_counts.get("critical", 0)
    medium = severity_counts.get("medium", 0)
    low = severity_counts.get("low", 0)

    summary = f"**ACR-QA Summary:** {risk['label']} ({risk['score']}/100) — "
    summary += f"🔴 {high} high | 🟡 {medium} medium | 🟢 {low} low"

    if high > 0:
        summary += (
            "\n\n⚠️ **Action Required:** Critical issues must be addressed before merge."
        )

    return summary


def print_summary(run_id: int = None):
    """Print summary to console"""
    print(generate_pr_summary(run_id))


if __name__ == "__main__":
    run_id = int(sys.argv[1]) if len(sys.argv) > 1 else None
    print_summary(run_id)
