import { useRelated } from "@/lib/queries";
import type { RelatedVuln } from "@/lib/api";
import { useNavigate } from "react-router-dom";
import { Link2, AlertTriangle, FileCode, Zap } from "lucide-react";

const EDGE_META: Record<RelatedVuln["edge_type"], { label: string; icon: React.ReactNode; color: string }> = {
  same_rule:   { label: "Same rule",    icon: <AlertTriangle size={12} aria-hidden />, color: "var(--sev-high)" },
  same_file:   { label: "Same file",    icon: <FileCode size={12} aria-hidden />,      color: "var(--accent-2)" },
  taint_chain: { label: "Taint chain",  icon: <Zap size={12} aria-hidden />,           color: "var(--sev-medium)" },
};

const SEV_COLOR: Record<string, string> = {
  high:   "var(--sev-high)",
  medium: "var(--sev-medium)",
  low:    "var(--sev-low)",
};

interface Props {
  vulnId: number | undefined;
}

export function RelatedObjects({ vulnId }: Props) {
  const navigate = useNavigate();
  const { data, isLoading, isError } = useRelated(vulnId);

  if (!vulnId) return null;
  if (isLoading) return <div className="related-list"><span className="spinner" style={{ width: 16, height: 16 }} aria-label="Loading related…" /></div>;
  if (isError)  return <div className="related-list" style={{ color: "var(--fg-4)", fontSize: 12 }}>Could not load related.</div>;
  if (!data || data.total === 0) return <div className="related-list" style={{ color: "var(--fg-4)", fontSize: 12 }}>No related vulnerabilities found.</div>;

  return (
    <ul className="related-list" role="list">
      {data.related.map((r) => {
        const meta = EDGE_META[r.edge_type] ?? EDGE_META.same_file;
        return (
          <li
            key={r.related_id}
            className="related-item"
            role="listitem"
            onClick={() => navigate(`/vuln/${r.short_id}`)}
            style={{ cursor: "pointer" }}
          >
            <span className="related-edge" style={{ color: meta.color }} title={meta.label}>
              {meta.icon}
            </span>
            <span className="related-sev" style={{ color: SEV_COLOR[r.severity] ?? "inherit" }}>
              {r.severity.slice(0, 1).toUpperCase()}
            </span>
            <span className="related-rule">{r.canonical_rule_id}</span>
            <span className="related-file">{r.file_path.split("/").slice(-2).join("/")}</span>
            <span className="related-status related-status--small">{r.status}</span>
          </li>
        );
      })}
    </ul>
  );
}

export function RelatedObjectsPanel({ vulnId }: Props) {
  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
        <Link2 size={14} aria-hidden style={{ color: "var(--fg-4)" }} />
        <span style={{ fontSize: 12, color: "var(--fg-4)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
          Related
        </span>
      </div>
      <RelatedObjects vulnId={vulnId} />
    </div>
  );
}
