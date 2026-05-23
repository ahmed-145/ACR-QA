import { Link } from "react-router-dom";
import { type Run } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { GitBranch, Clock } from "lucide-react";

interface Props { run: Run; }

export function ScanCard({ run }: Props) {
  const statusStyle: Record<string, { color: string; bg: string }> = {
    completed: { color: "var(--low-fg)", bg: "rgba(16,185,129,0.10)" },
    running:   { color: "var(--blue)",   bg: "rgba(96,165,250,0.10)" },
    failed:    { color: "var(--high-fg)", bg: "rgba(239,68,68,0.10)" },
    pending:   { color: "var(--fg-4)",   bg: "rgba(255,255,255,0.04)" },
  };
  const s = statusStyle[run.status] ?? statusStyle.pending;

  return (
    <Link to={`/runs/${run.id}`} style={{ textDecoration: "none" }}>
      <div className={`finding${run.high_count > 0 ? " high" : run.medium_count > 0 ? " med" : " low"}`}>
        {/* sev strip handled by .finding.high/.med/.low border-left */}
        <div className="finding-body" style={{ gridColumn: "1 / -1", display: "grid", gridTemplateColumns: "1fr auto", gap: 8, alignItems: "start" }}>
          <div>
            <div className="finding-msg" style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <GitBranch size={13} style={{ color: "var(--fg-4)", flexShrink: 0 }} aria-hidden />
              {run.repo_name}
              {run.pr_number && (
                <span style={{ fontSize: 12, color: "var(--fg-5)", fontFamily: "var(--mono)" }}>#{run.pr_number}</span>
              )}
            </div>
            <div className="finding-meta" style={{ marginTop: 4 }}>
              <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                <Clock size={10} aria-hidden /> {formatDate(run.started_at)}
              </span>
              <span className="sep">·</span>
              <span>{run.total_findings} findings</span>
            </div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 6 }}>
            <span style={{
              fontFamily: "var(--mono)", fontSize: 10, fontWeight: 700, padding: "2px 7px", borderRadius: 4,
              color: s.color, background: s.bg,
            }}>
              {run.status}
            </span>
            <div style={{ display: "flex", gap: 4 }}>
              {run.high_count > 0 && <span className="sev high">{run.high_count} HIGH</span>}
              {run.medium_count > 0 && <span className="sev med">{run.medium_count} MED</span>}
              {run.low_count > 0 && <span className="sev low">{run.low_count} LOW</span>}
            </div>
          </div>
        </div>
      </div>
    </Link>
  );
}
