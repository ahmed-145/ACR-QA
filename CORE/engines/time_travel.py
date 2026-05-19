"""
ACR-QA Time-Travel Vulnerability Analyzer (v5.0.0 Phase A.2).

Walks git history (bounded to last N commits, default 50) to answer:
    - When was a vulnerable line first introduced?
    - Who introduced it?
    - How many times has the pattern regressed (re-added after a deletion)?
    - Which commits touched the same area but did NOT fix the pattern
      ("near-fix" commits — review/refactor signals that missed the issue)?

Design notes:
    - Uses `git log -L start,end:file` for line-history when possible. Falls
      back to `git log --follow file` if the line is out of range or the
      line-log call fails.
    - Bounded by `max_commits` (default 50). The plan explicitly excludes
      unbounded `--full-history` mode — slips to Phase B.
    - Honest about scope: this is a heuristic. It does NOT claim semantic
      knowledge of whether a commit "fixed" the issue — only that it touched
      the same file/line region.
    - No external Python deps beyond stdlib + subprocess.
"""

from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Hard ceiling enforced everywhere. The CLI / API layer cannot exceed this.
MAX_COMMITS_CAP = 200
DEFAULT_MAX_COMMITS = 50


@dataclass
class CommitRef:
    sha: str
    date: str  # ISO 8601
    author: str
    subject: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class FindingHistory:
    file_path: str
    line_number: int | None
    rule_id: str | None
    first_seen_commit: CommitRef | None = None
    commits_touching: list[CommitRef] = field(default_factory=list)
    regression_count: int = 0
    near_fix_commits: list[CommitRef] = field(default_factory=list)
    bounded_by_max_commits: bool = True

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "rule_id": self.rule_id,
            "first_seen_commit": self.first_seen_commit.to_dict() if self.first_seen_commit else None,
            "first_seen_author": self.first_seen_commit.author if self.first_seen_commit else None,
            "first_seen_date": self.first_seen_commit.date if self.first_seen_commit else None,
            "commits_touching": [c.to_dict() for c in self.commits_touching],
            "regression_count": self.regression_count,
            "near_fix_commits": [c.to_dict() for c in self.near_fix_commits],
            "bounded_by_max_commits": self.bounded_by_max_commits,
        }


# ── git helpers ───────────────────────────────────────────────────────────────


_LOG_FORMAT = "%H%x1f%aI%x1f%an%x1f%s%x1e"  # sha, ISO date, author, subject — record sep \x1e


def _git(args: list[str], cwd: Path) -> str:
    """Run a git command with safe defaults; return stdout (decoded) or empty string."""
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.debug("git %s failed: %s", " ".join(args), exc)
        return ""
    if proc.returncode != 0:
        logger.debug("git %s exited %d: %s", " ".join(args), proc.returncode, proc.stderr[:300])
        return ""
    return proc.stdout


def _parse_log_records(output: str) -> list[CommitRef]:
    out: list[CommitRef] = []
    for chunk in output.split("\x1e"):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts = chunk.split("\x1f")
        if len(parts) < 4:
            continue
        sha, date, author, subject = parts[0], parts[1], parts[2], parts[3]
        out.append(CommitRef(sha=sha, date=date, author=author, subject=subject))
    return out


def _file_in_repo(repo_dir: Path, file_path: str) -> str | None:
    """Return the file path *relative to repo_dir*, or None if outside the repo."""
    repo_dir = repo_dir.resolve()
    p = Path(file_path)
    candidate = p if p.is_absolute() else (repo_dir / file_path)
    try:
        rel = candidate.resolve().relative_to(repo_dir)
    except (ValueError, OSError):
        return None
    return str(rel)


# ── Core analyzer ─────────────────────────────────────────────────────────────


class TimeTravelAnalyzer:
    """Analyse a finding's git-history footprint within a bounded commit window."""

    def __init__(self, repo_dir: str | Path, max_commits: int = DEFAULT_MAX_COMMITS):
        self.repo_dir = Path(repo_dir)
        self.max_commits = max(1, min(int(max_commits), MAX_COMMITS_CAP))

    # ── Public API ───────────────────────────────────────────────────────

    def analyze_finding(
        self,
        file_path: str,
        line_number: int | None = None,
        rule_id: str | None = None,
    ) -> FindingHistory:
        """Return the FindingHistory for the given location.

        If `line_number` is provided we use `git log -L` for precise line-history;
        otherwise we fall back to `git log --follow` over the file.
        """
        history = FindingHistory(file_path=file_path, line_number=line_number, rule_id=rule_id)

        if not self.is_git_repo():
            return history

        rel = _file_in_repo(self.repo_dir, file_path)
        if rel is None:
            return history

        commits = self._commits_touching_file_or_line(rel, line_number)
        history.commits_touching = commits

        if commits:
            history.first_seen_commit = commits[-1]  # oldest in the window

        history.regression_count = self._estimate_regression_count(commits)
        history.near_fix_commits = self._detect_near_fix_commits(commits, line_number)
        return history

    def is_git_repo(self) -> bool:
        return (self.repo_dir / ".git").exists() or _git(
            ["rev-parse", "--is-inside-work-tree"], self.repo_dir
        ).strip() == "true"

    # ── Internals ────────────────────────────────────────────────────────

    def _commits_touching_file_or_line(self, rel_path: str, line: int | None) -> list[CommitRef]:
        """Return ordered (newest → oldest) commits within the window."""
        # Prefer line-history when we have a sensible line number
        if line and line > 0:
            spec = f"{line},{line}:{rel_path}"
            args = [
                "log",
                f"-L{spec}",
                "--no-patch",
                "-s",
                f"--max-count={self.max_commits}",
                f"--pretty=format:{_LOG_FORMAT}",
            ]
            out = _git(args, self.repo_dir)
            commits = _parse_log_records(out)
            if commits:
                return commits

        # Fallback: per-file follow log
        args = [
            "log",
            "--follow",
            f"--max-count={self.max_commits}",
            f"--pretty=format:{_LOG_FORMAT}",
            "--",
            rel_path,
        ]
        out = _git(args, self.repo_dir)
        return _parse_log_records(out)

    @staticmethod
    def _estimate_regression_count(commits: list[CommitRef]) -> int:
        """Heuristic: count commit subjects that suggest a revert/re-add pattern.

        We treat the presence of `revert`, `re-add`, `reintroduce`, `bring back`,
        or `restore` (case-insensitive) in any subject as a regression signal.
        Bounded above by len(commits).
        """
        if not commits:
            return 0
        pattern = re.compile(r"\b(revert|re-?add|reintroduce|bring\s+back|restore)\b", re.IGNORECASE)
        return sum(1 for c in commits if pattern.search(c.subject))

    @staticmethod
    def _detect_near_fix_commits(commits: list[CommitRef], line: int | None) -> list[CommitRef]:
        """Approximation: commits whose subject mentions fix/cleanup/refactor but
        which appear *not* to be the first_seen commit.

        For the MVP we treat any non-oldest commit with `fix|cleanup|refactor|address`
        in the subject as a "near-fix" — it touched the area but the rule still
        triggers in the current scan, so by definition it didn't fully fix it.
        """
        if not commits or len(commits) < 2:
            return []
        pattern = re.compile(r"\b(fix|cleanup|refactor|address|harden|sanitize)\b", re.IGNORECASE)
        oldest = commits[-1].sha
        return [c for c in commits if c.sha != oldest and pattern.search(c.subject)]


# ── Convenience wrapper ───────────────────────────────────────────────────────


def analyze_finding_history(
    repo_dir: str | Path,
    file_path: str,
    line_number: int | None = None,
    rule_id: str | None = None,
    max_commits: int = DEFAULT_MAX_COMMITS,
) -> dict:
    """One-shot convenience used by the API endpoint."""
    return (
        TimeTravelAnalyzer(repo_dir, max_commits=max_commits)
        .analyze_finding(
            file_path=file_path,
            line_number=line_number,
            rule_id=rule_id,
        )
        .to_dict()
    )
