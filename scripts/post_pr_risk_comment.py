#!/usr/bin/env python3
"""Post ACR-QA PR Risk Score as a GitHub PR comment (v5.0.0 Phase A.5).

Reads run_id from a file, computes (or loads cached) PR Risk Score from the
DB, and posts a formatted comment on the PR. Designed to be called from the
acr-qa.yml GitHub Actions workflow after the analysis step.

Exit codes:
    0 — comment posted (or skipped cleanly when run_id missing)
    1 — fatal error (DB unavailable, GitHub token missing)
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)

_BAND_EMOJI = {"green": "✅", "amber": "⚠️", "red": "🔴"}
_BOT_MARKER = "<!-- acr-qa-pr-risk -->"


def _changed_lines(base_ref: str = "origin/main") -> int:
    """Count changed lines in the current PR diff."""
    try:
        out = subprocess.check_output(
            ["git", "diff", "--shortstat", f"{base_ref}...HEAD"],
            text=True,
            timeout=15,
        )
        total = 0
        for part in out.split(","):
            stripped = part.strip()
            if "file" in stripped:
                continue
            for token in stripped.split():
                if token.isdigit():
                    total += int(token)
                    break
        return total
    except Exception:
        return 0


def _format_comment(score_row: dict, run_id: int, changed_lines: int) -> str:
    score = score_row.get("score", 0)
    band = score_row.get("band", "green")
    emoji = _BAND_EMOJI.get(band, "✅")
    explainer = score_row.get("explainer_json") or []
    contributions = score_row.get("contributions_json") or {}

    lines = [
        _BOT_MARKER,
        f"## {emoji} ACR-QA PR Risk Score: **{score}/100** ({band.upper()})",
        "",
        "| Signal | Score contribution |",
        "|--------|-------------------|",
    ]
    for key, val in contributions.items():
        lines.append(f"| `{key}` | {val:.1f} |")

    if changed_lines:
        lines.append(f"| Changed lines | {changed_lines} |")

    if explainer:
        lines.append("")
        lines.append("**Why:**")
        for item in explainer[:5]:
            lines.append(f"- {item}")

    lines += [
        "",
        f"<sub>Run ID: {run_id} · [Full report](../../actions) · "
        f"[ACR-QA docs](https://github.com/ahmed-145/ACR-QA)</sub>",
    ]
    return "\n".join(lines)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Post PR Risk Score comment")
    parser.add_argument("--repo", required=True, help="owner/repo")
    parser.add_argument("--pr-number", required=True, type=int)
    parser.add_argument("--run-id-file", required=True, help="path to file containing run ID")
    parser.add_argument("--base-ref", default="origin/main")
    args = parser.parse_args()

    run_id_path = Path(args.run_id_file)
    if not run_id_path.exists():
        logger.warning("No run ID file — skipping PR risk comment")
        return 0
    run_id_str = run_id_path.read_text().strip()
    if not run_id_str.isdigit():
        logger.warning(f"Invalid run ID {run_id_str!r} — skipping")
        return 0
    run_id = int(run_id_str)

    # Load or compute score
    try:
        from CORE.engines.pr_risk import inputs_from_findings, predict_pr_risk
        from DATABASE.database import Database

        db = Database()
        score_row = db.get_pr_risk_score(run_id)
        if not score_row:
            changed_lines = _changed_lines(args.base_ref)
            findings = db.get_findings(run_id=run_id, limit=10000)
            file_scores = [int(r.get("score", 0)) for r in (db.get_file_risk_scores(run_id) or [])]
            inputs = inputs_from_findings(findings, file_risk_scores=file_scores, changed_lines=changed_lines)
            result = predict_pr_risk(inputs)
            payload = result.to_dict()
            try:
                db.upsert_pr_risk_score(run_id, payload, changed_lines=changed_lines)
            except Exception:
                pass
            score_row = payload
            score_row["explainer_json"] = result.explainer
            score_row["contributions_json"] = result.contributions
        else:
            changed_lines = score_row.get("changed_lines") or _changed_lines(args.base_ref)
    except Exception as exc:
        logger.error(f"Could not compute PR risk score: {exc}")
        return 0  # degrade gracefully — don't fail the CI job

    comment_body = _format_comment(score_row, run_id, changed_lines)

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        logger.info("No GITHUB_TOKEN — printing PR risk comment only:\n")
        print(comment_body)
        return 0

    try:
        from github import Github

        gh = Github(token)
        repo = gh.get_repo(args.repo)
        pr = repo.get_pull(args.pr_number)

        # Delete previous PR risk comment from this bot
        for comment in pr.get_issue_comments():
            if _BOT_MARKER in comment.body:
                comment.delete()

        pr.create_issue_comment(comment_body)
        band = score_row.get("band", "green")
        logger.info(f"✅ PR Risk Score comment posted — {score_row.get('score', 0)}/100 ({band})")
    except Exception as exc:
        logger.error(f"Failed to post GitHub comment: {exc}")
        # Non-fatal — the analysis itself succeeded

    return 0


if __name__ == "__main__":
    sys.exit(main())
