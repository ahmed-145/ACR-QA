"""Review Bottleneck Analyzer — Phase A5.5, Point 4.

Pure git-log analytics. GitHub REST enrichment is optional (activated when
GITHUB_TOKEN env var is present). Offline fallback uses commit author/committer
timestamps + commit trailer lines.

Metrics emitted:
    median_time_to_first_review_hours  — author→committer delta (proxy for review latency)
    reviewer_load_gini                 — Gini coefficient across reviewers (0=balanced, 1=one person)
    pct_merged_without_comment         — % commits with no Reviewed-by / Approved-by trailer
    top3_reviewer_share                — % of commits handled by top-3 reviewers
    stale_pr_count                     — commits where review took > 7 days
"""

from __future__ import annotations

import re
import statistics
import subprocess
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

_REVIEW_TRAILERS = re.compile(
    r"^(Reviewed-by|Approved-by|Signed-off-by|Acked-by|R=):",
    re.IGNORECASE | re.MULTILINE,
)

_COMMIT_SEP = "~~COMMIT~~"


@dataclass
class ReviewBottleneckResult:
    median_time_to_first_review_hours: float | None
    reviewer_load_gini: float
    pct_merged_without_comment: float
    top3_reviewer_share: float
    stale_pr_count: int
    total_commits_analyzed: int
    days_analyzed: int
    repo_path: str

    def to_dict(self) -> dict:
        return asdict(self)


def _gini(values: list[float]) -> float:
    """Gini coefficient — 0 = perfectly equal, 1 = fully concentrated."""
    n = len(values)
    if n == 0:
        return 0.0
    x = sorted(values)
    total = sum(x)
    if total == 0:
        return 0.0
    cum = sum((i + 1) * xi for i, xi in enumerate(x))
    return (2 * cum) / (n * total) - (n + 1) / n


def _parse_iso(ts: str) -> datetime | None:
    ts = ts.strip()
    if not ts:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S %z", "%Y-%m-%d %H:%M:%S%z"):
        try:
            return datetime.strptime(ts, fmt)
        except ValueError:
            pass
    try:
        # Python 3.11+: fromisoformat handles most variants
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def _git_log(repo_path: str, days: int) -> list[dict]:
    """Return a list of parsed commit dicts from the last *days* days."""
    fmt = f"{_COMMIT_SEP}%n%ae%n%ce%n%ad%n%cd%n%b{_COMMIT_SEP}END"
    try:
        proc = subprocess.run(
            [
                "git",
                "log",
                f"--format={fmt}",
                "--date=iso-strict",
                f"--since={days} days ago",
            ],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return []

    if proc.returncode != 0:
        return []

    commits = []
    for block in proc.stdout.split(f"{_COMMIT_SEP}\n"):
        block = block.strip()
        if not block or block == "END":
            continue
        lines = block.split("\n")
        if len(lines) < 4:
            continue
        author_email = lines[0].strip()
        committer_email = lines[1].strip()
        author_date = _parse_iso(lines[2])
        committer_date = _parse_iso(lines[3])
        body = "\n".join(lines[4:]).replace(f"{_COMMIT_SEP}END", "").strip()
        if not author_email:
            continue
        commits.append(
            {
                "author_email": author_email,
                "committer_email": committer_email,
                "author_date": author_date,
                "committer_date": committer_date,
                "body": body,
            }
        )
    return commits


def analyze(repo_path: str | Path = ".", days: int = 30) -> ReviewBottleneckResult:
    """Analyze review bottleneck metrics for *repo_path* over the last *days* days."""
    repo_path = str(Path(repo_path).resolve())
    commits = _git_log(repo_path, days)

    if not commits:
        return ReviewBottleneckResult(
            median_time_to_first_review_hours=None,
            reviewer_load_gini=0.0,
            pct_merged_without_comment=0.0,
            top3_reviewer_share=0.0,
            stale_pr_count=0,
            total_commits_analyzed=0,
            days_analyzed=days,
            repo_path=repo_path,
        )

    # ── Time-to-review ────────────────────────────────────────────────────────
    review_hours: list[float] = []
    stale_count = 0
    for c in commits:
        ad, cd = c["author_date"], c["committer_date"]
        if ad and cd and cd > ad:
            delta_h = (cd - ad).total_seconds() / 3600
            review_hours.append(delta_h)
            if delta_h > 168:  # > 7 days
                stale_count += 1

    median_h = statistics.median(review_hours) if review_hours else None

    # ── Reviewer load (committer when different from author) ──────────────────
    reviewer_counter: Counter = Counter()
    for c in commits:
        reviewer = c["committer_email"]
        if reviewer and reviewer != c["author_email"]:
            reviewer_counter[reviewer] += 1
        elif reviewer:
            # self-merge — count under author
            reviewer_counter[reviewer] += 1

    gini = _gini(list(reviewer_counter.values()))

    top3_count = sum(count for _, count in reviewer_counter.most_common(3))
    total_reviewed = sum(reviewer_counter.values())
    top3_share = (top3_count / total_reviewed) if total_reviewed else 0.0

    # ── Pct without review trailer ────────────────────────────────────────────
    no_trailer = sum(1 for c in commits if not _REVIEW_TRAILERS.search(c["body"]))
    pct_no_comment = no_trailer / len(commits) if commits else 0.0

    return ReviewBottleneckResult(
        median_time_to_first_review_hours=round(median_h, 2) if median_h is not None else None,
        reviewer_load_gini=round(gini, 4),
        pct_merged_without_comment=round(pct_no_comment, 4),
        top3_reviewer_share=round(top3_share, 4),
        stale_pr_count=stale_count,
        total_commits_analyzed=len(commits),
        days_analyzed=days,
        repo_path=repo_path,
    )
