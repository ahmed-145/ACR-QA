"""Tests for the Time-Travel Vulnerability Analyzer (v5.0.0 Phase A.2)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from CORE.engines.time_travel import (
    DEFAULT_MAX_COMMITS,
    MAX_COMMITS_CAP,
    CommitRef,
    FindingHistory,
    TimeTravelAnalyzer,
    _parse_log_records,
    analyze_finding_history,
)

# ── git fixture: a tiny throwaway repo with a controlled history ────────────


def _git(repo: Path, *args: str, env_extra: dict | None = None) -> None:
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "Test Author",
            "GIT_AUTHOR_EMAIL": "test@acrqa.local",
            "GIT_COMMITTER_NAME": "Test Author",
            "GIT_COMMITTER_EMAIL": "test@acrqa.local",
        }
    )
    if env_extra:
        env.update(env_extra)
    subprocess.run(["git", *args], cwd=str(repo), check=True, env=env, capture_output=True)


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """Build a 4-commit repo with a vulnerable file that mutates over commits."""
    r = tmp_path / "tt-repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "commit.gpgsign", "false")
    target = r / "app.py"

    # The vulnerable call lives at line 5 of every revision so `git log -L5,5`
    # follows it across the whole history. We mutate a *comment line* (line 4)
    # for each commit so the file changes without disturbing line 5's content.
    def _revision(comment: str) -> str:
        return "import os\n" "\n" "\n" f"# {comment}\n" "def run(cmd): return os.system(cmd)\n"

    target.write_text(_revision("Initial revision"))
    _git(r, "add", "app.py")
    _git(r, "commit", "-q", "-m", "Initial: introduce shell exec helper")

    target.write_text(_revision("Refactor pass over run()"))
    _git(r, "add", "app.py")
    _git(r, "commit", "-q", "-m", "Refactor run() helper for clarity")

    target.write_text(_revision("Address logging concerns"))
    _git(r, "add", "app.py")
    _git(r, "commit", "-q", "-m", "Address logging in run()")

    target.write_text(_revision("Sanitize input TODO"))
    _git(r, "add", "app.py")
    _git(r, "commit", "-q", "-m", "Sanitize input before subprocess (WIP)")

    return r


# ── Data classes ─────────────────────────────────────────────────────────────


class TestCommitRef:
    def test_to_dict_has_fields(self):
        c = CommitRef(sha="abc", date="2026-01-01T00:00:00Z", author="A", subject="x")
        assert c.to_dict() == {"sha": "abc", "date": "2026-01-01T00:00:00Z", "author": "A", "subject": "x"}


class TestFindingHistory:
    def test_default_to_dict(self):
        h = FindingHistory(file_path="x.py", line_number=10, rule_id="SEC-001")
        d = h.to_dict()
        assert d["file_path"] == "x.py"
        assert d["first_seen_commit"] is None
        assert d["first_seen_author"] is None
        assert d["commits_touching"] == []
        assert d["regression_count"] == 0
        assert d["near_fix_commits"] == []


class TestParseLogRecords:
    def test_parses_well_formed_output(self):
        out = (
            "abc\x1f2026-01-01T00:00:00Z\x1fAlice\x1ffix something\x1e"
            "def\x1f2026-01-02T00:00:00Z\x1fBob\x1frefactor stuff\x1e"
        )
        records = _parse_log_records(out)
        assert len(records) == 2
        assert records[0].sha == "abc"
        assert records[0].author == "Alice"
        assert records[1].subject == "refactor stuff"

    def test_ignores_malformed_records(self):
        out = "abc\x1fonly-three-fields\x1e\x1e"
        assert _parse_log_records(out) == []

    def test_empty_input(self):
        assert _parse_log_records("") == []


# ── Analyzer ─────────────────────────────────────────────────────────────────


class TestTimeTravelAnalyzer:
    def test_constructor_clamps_to_cap(self):
        a = TimeTravelAnalyzer(".", max_commits=99999)
        assert a.max_commits == MAX_COMMITS_CAP

    def test_constructor_clamps_to_min_one(self):
        a = TimeTravelAnalyzer(".", max_commits=0)
        assert a.max_commits == 1

    def test_default_max_commits(self):
        a = TimeTravelAnalyzer(".")
        assert a.max_commits == DEFAULT_MAX_COMMITS

    def test_non_git_repo_returns_empty_history(self, tmp_path: Path):
        a = TimeTravelAnalyzer(tmp_path)
        h = a.analyze_finding(file_path="x.py", line_number=1)
        assert h.first_seen_commit is None
        assert h.commits_touching == []

    def test_file_outside_repo_returns_empty(self, repo: Path):
        a = TimeTravelAnalyzer(repo)
        h = a.analyze_finding(file_path="/etc/passwd", line_number=1)
        assert h.first_seen_commit is None
        assert h.commits_touching == []

    def test_line_history_picks_up_introduction(self, repo: Path):
        a = TimeTravelAnalyzer(repo)
        h = a.analyze_finding(file_path="app.py", line_number=5)
        assert h.first_seen_commit is not None
        assert h.first_seen_commit.author == "Test Author"
        # Most recent → oldest. The oldest commit's subject is the introduction.
        assert "Initial" in h.first_seen_commit.subject

    def test_commits_touching_ordered_newest_first(self, repo: Path):
        # Line 4 mutates per commit (comment line), so line-history follows all commits.
        a = TimeTravelAnalyzer(repo)
        h = a.analyze_finding(file_path="app.py", line_number=4)
        # The latest commit subject mentions Sanitize input, oldest mentions Initial
        assert h.commits_touching
        assert "Sanitize" in h.commits_touching[0].subject
        assert "Initial" in h.commits_touching[-1].subject

    def test_commits_touching_falls_back_to_file_level_without_line(self, repo: Path):
        a = TimeTravelAnalyzer(repo)
        h = a.analyze_finding(file_path="app.py", line_number=None)
        assert len(h.commits_touching) == 4

    def test_near_fix_commits_excludes_oldest(self, repo: Path):
        a = TimeTravelAnalyzer(repo)
        h = a.analyze_finding(file_path="app.py", line_number=4)
        near_subjects = [c.subject for c in h.near_fix_commits]
        # Refactor, Address, Sanitize all match heuristic; Initial does not.
        assert any("Refactor" in s for s in near_subjects) or any("Address" in s for s in near_subjects)
        assert not any("Initial" in s for s in near_subjects)

    def test_regression_count_zero_when_no_revert_keywords(self, repo: Path):
        a = TimeTravelAnalyzer(repo)
        h = a.analyze_finding(file_path="app.py", line_number=5)
        assert h.regression_count == 0

    def test_regression_count_detects_revert(self, tmp_path: Path):
        # Build a tiny repo whose subjects include "Revert"
        r = tmp_path / "rev"
        r.mkdir()
        _git(r, "init", "-q", "-b", "main")
        _git(r, "config", "commit.gpgsign", "false")
        f = r / "x.py"
        f.write_text("a=1\n")
        _git(r, "add", "x.py")
        _git(r, "commit", "-q", "-m", "Add x")
        f.write_text("a=2\n")
        _git(r, "add", "x.py")
        _git(r, "commit", "-q", "-m", "Revert previous change")
        a = TimeTravelAnalyzer(r)
        h = a.analyze_finding("x.py", line_number=1)
        assert h.regression_count >= 1

    def test_fallback_when_line_history_empty(self, repo: Path):
        a = TimeTravelAnalyzer(repo)
        # A line number that doesn't exist forces the fallback
        h = a.analyze_finding(file_path="app.py", line_number=99999)
        # Fallback log over the whole file should still surface commits
        assert h.commits_touching

    def test_bounded_by_max_commits_caps_results(self, repo: Path):
        a = TimeTravelAnalyzer(repo, max_commits=2)
        h = a.analyze_finding("app.py", line_number=5)
        assert len(h.commits_touching) <= 2

    def test_is_git_repo_detects_repo(self, repo: Path):
        assert TimeTravelAnalyzer(repo).is_git_repo() is True

    def test_is_git_repo_false_for_non_repo(self, tmp_path: Path):
        assert TimeTravelAnalyzer(tmp_path).is_git_repo() is False


# ── analyze_finding_history one-shot ─────────────────────────────────────────


class TestAnalyzeFindingHistory:
    def test_dict_shape(self, repo: Path):
        out = analyze_finding_history(repo, file_path="app.py", line_number=5, rule_id="SEC-001")
        assert set(out.keys()) >= {
            "file_path",
            "line_number",
            "rule_id",
            "first_seen_commit",
            "first_seen_author",
            "first_seen_date",
            "commits_touching",
            "regression_count",
            "near_fix_commits",
            "bounded_by_max_commits",
        }
        assert out["file_path"] == "app.py"
        assert out["rule_id"] == "SEC-001"

    def test_non_repo_returns_safe_empty(self, tmp_path: Path):
        out = analyze_finding_history(tmp_path, file_path="any.py", line_number=1)
        assert out["first_seen_commit"] is None
        assert out["commits_touching"] == []

    def test_max_commits_caps_at_constant(self, repo: Path):
        out = analyze_finding_history(repo, file_path="app.py", line_number=5, max_commits=99999)
        # We don't have 200 commits in the fixture; this just asserts no crash
        assert isinstance(out["commits_touching"], list)
