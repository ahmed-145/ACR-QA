#!/usr/bin/env python3
"""
Post ACR-QA quality gate result as a top-level GitHub PR comment.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from github import Github

from DATABASE.database import Database

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Post quality gate comment to PR")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--pr-number", required=True, type=int)
    parser.add_argument("--run-id-file", required=True)
    args = parser.parse_args()

    # Read run ID
    run_id_path = Path(args.run_id_file)
    if not run_id_path.exists():
        logger.error("⚠️  No run ID file found — skipping gate comment")
        sys.exit(0)

    run_id_str = run_id_path.read_text().strip()
    if not run_id_str.isdigit():
        logger.error(f"⚠️  Invalid run ID: {run_id_str!r} — skipping gate comment")
        sys.exit(0)

    run_id = int(run_id_str)

    # Load findings from DB
    db = Database()
    findings = db.get_findings_for_run(run_id)

    # Re-evaluate gate using current .acrqa.yml config
    import yaml

    from CORE.engines.quality_gate import QualityGate

    config = {}
    if Path(".acrqa.yml").exists():
        with open(".acrqa.yml") as f:
            config = yaml.safe_load(f) or {}

    gate = QualityGate(config=config)
    result = gate.evaluate(findings)
    comment_body = gate.format_gate_comment(result)

    # Post to GitHub
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        logger.error("⚠️  No GITHUB_TOKEN — printing gate result only")
        logger.info(comment_body)
        sys.exit(0)

    gh = Github(token)
    repo = gh.get_repo(args.repo)
    pr = repo.get_pull(args.pr_number)

    # Delete any previous gate comment from this bot
    bot_marker = "🚦 ACR-QA Quality Gate"
    for comment in pr.get_issue_comments():
        if bot_marker in comment.body and comment.user.type == "Bot":
            comment.delete()

    pr.create_issue_comment(comment_body)
    status = "PASSED ✅" if result["passed"] else "FAILED ❌"
    logger.info(f"✅ Gate comment posted — {status}")

    # Exit 0 always — blocking is handled by the workflow step
    sys.exit(0)


if __name__ == "__main__":
    main()
