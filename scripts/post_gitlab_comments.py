#!/usr/bin/env python3
"""
Post ACR-QA findings as GitLab Merge Request comments
"""
import sys
import os
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from DATABASE.database import Database

try:
    import gitlab
except ImportError:
    print("❌ python-gitlab not installed. Run: pip install python-gitlab")
    sys.exit(1)


def format_findings_for_gitlab(findings):
    """
    Format findings as GitLab MR comment

    Args:
        findings: List of finding dicts from database

    Returns:
        Formatted markdown comment
    """
    if not findings:
        return "✅ **ACR-QA Analysis Complete** - No issues found!"

    # Group by severity
    by_severity = {"high": [], "medium": [], "low": []}
    for f in findings:
        sev = f.get("canonical_severity", "low")
        if sev in by_severity:
            by_severity[sev].append(f)

    lines = ["## 🤖 ACR-QA Code Review", ""]

    # Summary
    total = len(findings)
    lines.append(f"**Found {total} issue(s)**")
    lines.append("")
    lines.append(
        f"- 🔴 High: {len(by_severity['high'])} | "
        f"🟡 Medium: {len(by_severity['medium'])} | "
        f"🟢 Low: {len(by_severity['low'])}"
    )
    lines.append("")

    # High severity
    if by_severity["high"]:
        lines.append("### 🔴 Critical Issues")
        lines.append("")
        for f in by_severity["high"][:5]:  # Limit to 5
            canonical_id = f.get("canonical_rule_id", f["rule_id"])
            lines.append(f"**{canonical_id}** - `{f['file_path']}:{f['line_number']}`")
            lines.append(f"> {f['message']}")
            if f.get("explanation_text"):
                lines.append(f"\n{f['explanation_text'][:200]}...")
            lines.append("")

    # Medium severity
    if by_severity["medium"]:
        lines.append("### 🟡 Medium Priority")
        lines.append("")
        for f in by_severity["medium"][:3]:
            canonical_id = f.get("canonical_rule_id", f["rule_id"])
            lines.append(f"**{canonical_id}** - `{f['file_path']}:{f['line_number']}`")
            lines.append(f"> {f['message']}")
            lines.append("")

    lines.append("---")
    lines.append("*Powered by ACR-QA v2.0 with RAG-enhanced explanations*")

    return "\n".join(lines)


def post_gitlab_comment(project_id, mr_iid, comment_body, token):
    """
    Post comment to GitLab MR

    Args:
        project_id: GitLab project ID
        mr_iid: Merge request IID
        comment_body: Comment text
        token: GitLab access token
    """
    gl = gitlab.Gitlab(url="https://gitlab.com", private_token=token)
    project = gl.projects.get(project_id)
    mr = project.mergerequests.get(mr_iid)

    # Post comment
    mr.notes.create({"body": comment_body})
    print(f"✅ Posted comment to MR !{mr_iid}")


def main():
    parser = argparse.ArgumentParser(description="Post ACR-QA findings to GitLab MR")
    parser.add_argument("--project-id", required=True, help="GitLab project ID")
    parser.add_argument("--mr-iid", type=int, required=True, help="Merge request IID")
    parser.add_argument("--token", help="GitLab access token (or use GITLAB_TOKEN env)")
    parser.add_argument("--run-id", type=int, help="Analysis run ID (default: latest)")

    args = parser.parse_args()

    # Get token
    token = args.token or os.getenv("GITLAB_TOKEN")
    if not token:
        print("❌ GitLab token required (--token or GITLAB_TOKEN env)")
        sys.exit(1)

    # Get findings
    db = Database()
    if args.run_id:
        findings = db.get_findings_with_explanations(args.run_id)
    else:
        runs = db.get_recent_runs(limit=1)
        if not runs:
            print("❌ No analysis runs found")
            sys.exit(1)
        findings = db.get_findings_with_explanations(runs[0]["id"])

    # Format and post
    comment = format_findings_for_gitlab(findings)
    post_gitlab_comment(args.project_id, args.mr_iid, comment, token)


if __name__ == "__main__":
    main()
