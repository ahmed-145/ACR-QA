/**
 * Time-Travel finding history (v5.0.0 Phase A.2).
 *
 * Surfaces who introduced the vulnerable line, when, and which commits
 * touched the same area without fully fixing it. Pure-SVG strip diagram.
 */

import { useEffect, useState } from "react";
import { authHeader } from "@/lib/auth";

interface CommitRef {
  sha: string;
  date: string;
  author: string;
  subject: string;
}

interface FindingHistoryData {
  finding_id: number;
  file_path: string;
  line_number: number | null;
  rule_id: string | null;
  first_seen_commit: CommitRef | null;
  first_seen_author: string | null;
  first_seen_date: string | null;
  commits_touching: CommitRef[];
  regression_count: number;
  near_fix_commits: CommitRef[];
  bounded_by_max_commits: boolean;
}

interface Props {
  findingId: number;
  className?: string;
}

function shortSha(s: string): string {
  return s.slice(0, 7);
}

export function FindingHistory({ findingId, className }: Props) {
  const [data, setData] = useState<FindingHistoryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    fetch(`/v1/findings/${findingId}/history`, { headers: authHeader() })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((d: FindingHistoryData) => {
        if (alive) setData(d);
      })
      .catch((e) => alive && setError(e instanceof Error ? e.message : "fetch failed"))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [findingId]);

  if (loading) {
    return (
      <div data-testid="history-loading" className={`text-xs text-muted-foreground ${className ?? ""}`}>
        Loading time-travel history…
      </div>
    );
  }
  if (error) {
    return (
      <div data-testid="history-error" role="alert" className={`text-xs text-destructive ${className ?? ""}`}>
        {error}
      </div>
    );
  }
  if (!data) return null;

  const empty =
    !data.first_seen_commit && data.commits_touching.length === 0 && data.near_fix_commits.length === 0;

  if (empty) {
    return (
      <div data-testid="history-empty" className={`text-xs text-muted-foreground ${className ?? ""}`}>
        No git history available (workspace is not a git repository).
      </div>
    );
  }

  const nearFixShas = new Set(data.near_fix_commits.map((c) => c.sha));

  return (
    <div data-testid="history" className={`flex flex-col gap-3 rounded-md border bg-card p-4 ${className ?? ""}`}>
      <header className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Time-Travel History</h3>
        <span className="text-[10px] text-muted-foreground">bounded · max 50 commits</span>
      </header>

      <dl className="grid grid-cols-2 gap-2 text-xs">
        <dt className="text-muted-foreground">first seen</dt>
        <dd data-testid="first-seen-commit" className="font-mono">
          {data.first_seen_commit
            ? `${shortSha(data.first_seen_commit.sha)} · ${data.first_seen_commit.author}`
            : "—"}
        </dd>
        <dt className="text-muted-foreground">when</dt>
        <dd data-testid="first-seen-date" className="font-mono">
          {data.first_seen_date ?? "—"}
        </dd>
        <dt className="text-muted-foreground">regression count</dt>
        <dd data-testid="regression-count" className="font-mono">
          {data.regression_count}
        </dd>
        <dt className="text-muted-foreground">commits touching</dt>
        <dd data-testid="commits-touching-count" className="font-mono">
          {data.commits_touching.length}
        </dd>
      </dl>

      <ol
        data-testid="commits-strip"
        className="flex flex-col gap-1 rounded border bg-muted/20 p-2 text-xs"
        aria-label="Commits touching this finding (newest first)"
      >
        {data.commits_touching.map((c) => {
          const isFirstSeen = data.first_seen_commit?.sha === c.sha;
          const isNearFix = nearFixShas.has(c.sha);
          return (
            <li
              key={c.sha}
              data-testid={`commit-${c.sha}`}
              data-near-fix={isNearFix ? "1" : "0"}
              data-first-seen={isFirstSeen ? "1" : "0"}
              className={
                "grid grid-cols-[80px_1fr_auto] items-center gap-2 px-2 py-1 " +
                (isFirstSeen ? "rounded bg-red-500/10" : isNearFix ? "rounded bg-amber-500/10" : "")
              }
            >
              <span className="font-mono text-[11px] text-muted-foreground">{shortSha(c.sha)}</span>
              <span className="truncate">{c.subject}</span>
              <span className="text-[10px] text-muted-foreground">{c.author}</span>
            </li>
          );
        })}
      </ol>

      {data.near_fix_commits.length > 0 && (
        <p data-testid="near-fix-note" className="text-[10px] text-muted-foreground">
          <strong>{data.near_fix_commits.length}</strong> commit(s) touched the area but did not fully
          fix the pattern (amber = near-fix; red = first-seen).
        </p>
      )}
    </div>
  );
}
