# Time-Travel Vulnerability Analyzer

**Module:** `CORE/engines/time_travel.py`
**Introduced:** v5.0.0 Phase A.2 (May 19, 2026)
**Status:** GA — bounded git-history analysis. `--full-history` mode deferred to Phase B.

## What it answers

For a single finding (`file`, `line`, `rule_id`), the analyzer surfaces:

| Field | Meaning |
|---|---|
| `first_seen_commit` | The oldest commit in the bounded window that introduced the line's current content. |
| `first_seen_author` / `first_seen_date` | Convenience accessors on `first_seen_commit`. |
| `commits_touching` | Ordered list (newest → oldest) of commits in the window that touched the line / file. |
| `regression_count` | Count of commit subjects in the window matching `revert / re-add / reintroduce / bring back / restore`. |
| `near_fix_commits` | Commits whose subject mentions `fix / cleanup / refactor / address / harden / sanitize` and are NOT the introducing commit — i.e. commits that touched the area but did not fully fix the rule. |
| `bounded_by_max_commits` | Always `true` in A2. Always `true` until `--full-history` lands in Phase B. |

## How it works

1. `TimeTravelAnalyzer(repo_dir, max_commits=N)` (default `N=50`, capped at `MAX_COMMITS_CAP=200`).
2. If `file_path` resolves outside the repo, return an empty `FindingHistory`.
3. If a line number is provided, run

   ```
   git log -L<line>,<line>:<file> --no-patch -s --max-count=N --pretty=format:%H\x1f%aI\x1f%an\x1f%s\x1e
   ```

   `git log -L` follows that exact line back through history.
4. If line-history returns nothing (line out of range, deleted, never existed), fall
   back to `git log --follow --max-count=N -- <file>` — file-level history.
5. Parse the `\x1e`-record / `\x1f`-field output into `CommitRef` dataclasses.
6. Apply two heuristics over the commit subjects:
   - **Regression count** — regex `\b(revert|re-?add|reintroduce|bring\s+back|restore)\b`
   - **Near-fix commits** — regex `\b(fix|cleanup|refactor|address|harden|sanitize)\b`,
     excluding the oldest (introducing) commit.

## Hard caps

- `max_commits` is clamped to `[1, 200]` in `__init__`.
- `git` subprocess calls have a 20s `timeout`.
- Failing `git` commands return empty results; the engine never raises.

## What it does NOT do (v5.0.0 A2 scope)

- **No semantic "fix" detection.** The near-fix list is a heuristic over commit
  *subjects*, not diff content. A commit that genuinely fixed the issue but called
  itself "fix" would still appear here if the line still triggers in the current
  scan — and that signal is *intentional* (it means the fix landed but the rule
  still fires).
- **No author-trust scoring.** Per plan v3 Drop-First — slips to Phase B.
- **No cross-file dataflow.** Single-file line / file history only.
- **No unbounded history.** `--full-history` opt-in is Phase B.

## Endpoint

`GET /v1/findings/{fid}/history?max_commits=50`

Looks up the finding, calls `analyze_finding_history(repo_dir=cwd, file, line, rule_id, max_commits)`,
and returns the dict with `finding_id` added.

If the workspace isn't a git repo, the response has empty `commits_touching` and `null` for
`first_seen_commit` — the engine never errors.

## Database

Migration `0014` adds a `finding_history` cache table (one row per finding) with:
`first_seen_commit`, `first_seen_author`, `first_seen_date`, `regression_count`,
`commits_touching` (JSON), `near_fix_commits` (JSON), `max_commits`, `computed_at`.

The table is a *cache* — A2 always re-computes on demand. A scheduled background
populator is Phase B.

## Complexity

- O(N · t_git) where N is `max_commits` and t_git is the cost of one `git log` call
  (a few ms for small repos, up to a few hundred ms for trunk-of-Flask scale).
- Tested with a 4-commit synthetic repo (23 unit tests) and against the ACR-QA repo
  itself (smoke).

## Testing

`TESTS/test_time_travel.py` (23 tests) builds throwaway repos per test using a
controlled commit history.
