import { Link } from "react-router-dom";
import { useRuns } from "@/lib/queries";
import { formatDate } from "@/lib/utils";
import { GitBranch, Clock } from "lucide-react";

interface RepoSummary {
  repo_name: string;
  total_runs: number;
  last_run_id: number;
  last_run_status: string;
  last_run_at: string;
  total_findings: number;
  high_count: number;
}

export function ReposPage() {
  const { data: runsData, isLoading } = useRuns(100);
  const runs = runsData?.runs ?? [];

  // Aggregate by repo
  const repoMap = new Map<string, RepoSummary>();
  for (const run of runs) {
    const existing = repoMap.get(run.repo_name);
    if (!existing || run.id > existing.last_run_id) {
      repoMap.set(run.repo_name, {
        repo_name: run.repo_name,
        total_runs: (existing?.total_runs ?? 0) + 1,
        last_run_id: run.id,
        last_run_status: run.status,
        last_run_at: run.started_at,
        total_findings: (existing?.total_findings ?? 0) + run.total_findings,
        high_count: (existing?.high_count ?? 0) + run.high_count,
      });
    } else {
      existing.total_runs += 1;
      existing.total_findings += run.total_findings;
      existing.high_count += run.high_count;
    }
  }
  const repos = Array.from(repoMap.values()).sort((a, b) => b.last_run_id - a.last_run_id);

  const statusStyle: Record<string, { color: string; bg: string }> = {
    completed: { color: "var(--low-fg)", bg: "rgba(16,185,129,0.10)" },
    running:   { color: "var(--blue)",   bg: "rgba(96,165,250,0.10)" },
    failed:    { color: "var(--high-fg)", bg: "rgba(239,68,68,0.10)" },
    pending:   { color: "var(--fg-4)",   bg: "rgba(255,255,255,0.04)" },
  };

  return (
    <>
      <div className="topbar">
        <div className="crumbs">
          <span className="cur">Repositories</span>
        </div>
        <span className="grow" />
        <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--fg-4)" }}>
          {repos.length} repos
        </span>
      </div>

      <div className="page-pad">
        <h1 className="title">Repositories</h1>
        <p className="subtitle">All scanned repos with last-run status and aggregate findings</p>

        <div className="stats" style={{ gridTemplateColumns: "repeat(3, 1fr)", marginBottom: 24 }}>
          <div className="stat">
            <div className="lbl">Repositories</div>
            <div className="num">{repos.length}</div>
          </div>
          <div className="stat">
            <div className="lbl">Total Runs</div>
            <div className="num">{runs.length}</div>
          </div>
          <div className="stat">
            <div className="lbl">Total Findings</div>
            <div className="num">{repos.reduce((s, r) => s + r.total_findings, 0)}</div>
          </div>
        </div>

        {isLoading ? (
          <div className="empty"><span className="spinner" /> Loading repos…</div>
        ) : repos.length === 0 ? (
          <div className="empty">No repositories scanned yet. Run your first scan on the dashboard.</div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {repos.map((repo) => {
              const s = statusStyle[repo.last_run_status] ?? statusStyle.pending;
              return (
                <Link
                  key={repo.repo_name}
                  to={`/runs/${repo.last_run_id}`}
                  style={{ textDecoration: "none" }}
                >
                  <div className={`finding${repo.high_count > 0 ? " high" : " low"}`}
                    style={{ cursor: "pointer" }}
                  >
                    <div className="finding-body" style={{
                      gridColumn: "1 / -1", display: "grid",
                      gridTemplateColumns: "1fr auto", gap: 12, alignItems: "center",
                    }}>
                      <div>
                        <div className="finding-msg" style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <GitBranch size={13} style={{ color: "var(--fg-4)", flexShrink: 0 }} aria-hidden />
                          <span style={{ fontWeight: 600, color: "var(--fg)" }}>{repo.repo_name}</span>
                        </div>
                        <div className="finding-meta" style={{ marginTop: 4 }}>
                          <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                            <Clock size={10} aria-hidden />
                            {formatDate(repo.last_run_at)}
                          </span>
                          <span className="sep">·</span>
                          <span>{repo.total_runs} runs</span>
                          <span className="sep">·</span>
                          <span>{repo.total_findings} findings total</span>
                        </div>
                      </div>
                      <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 6 }}>
                        <span style={{
                          fontFamily: "var(--mono)", fontSize: 10, fontWeight: 700,
                          padding: "2px 7px", borderRadius: 4,
                          color: s.color, background: s.bg,
                        }}>{repo.last_run_status}</span>
                        <div style={{ display: "flex", gap: 4 }}>
                          {repo.high_count > 0 && <span className="sev high">{repo.high_count} HIGH</span>}
                          <span className="id-pill">Run #{repo.last_run_id}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </>
  );
}
