import type { FleetRepoRow } from "@/lib/api";

interface Props {
  repos: FleetRepoRow[];
}

const COLS = [
  { key: "open_high" as const, label: "HIGH",   color: "var(--sev-high)" },
  { key: "open_med"  as const, label: "MED",    color: "var(--sev-medium)" },
  { key: "open_low"  as const, label: "LOW",    color: "var(--sev-low)" },
  { key: "regressions" as const, label: "REGR", color: "var(--accent-2)" },
];

function cellBg(value: number, max: number, color: string): string {
  if (max === 0 || value === 0) return "transparent";
  const opacity = Math.max(0.08, Math.min(0.85, value / max));
  return color.replace("var(--sev-high)", `rgba(239,68,68,${opacity})`)
              .replace("var(--sev-medium)", `rgba(245,158,11,${opacity})`)
              .replace("var(--sev-low)", `rgba(34,197,94,${opacity})`)
              .replace("var(--accent-2)", `rgba(139,92,246,${opacity})`);
}

export function RepoHeatmap({ repos }: Props) {
  if (!repos.length) return (
    <div style={{ color: "var(--fg-5)", fontSize: 13, padding: "12px 0" }}>No repo data.</div>
  );

  const maxes = COLS.reduce((acc, c) => {
    acc[c.key] = Math.max(...repos.map((r) => r[c.key]), 1);
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className="heatmap-wrap" role="table" aria-label="Repo risk heatmap">
      {/* Header */}
      <div className="heatmap-row heatmap-header" role="row">
        <div className="heatmap-repo-cell" role="columnheader">REPO</div>
        {COLS.map((c) => (
          <div key={c.key} className="heatmap-cell" role="columnheader"
               style={{ color: c.color, fontWeight: 700 }}>
            {c.label}
          </div>
        ))}
        <div className="heatmap-cell" role="columnheader">SCANS</div>
      </div>

      {/* Data rows */}
      {repos.map((r) => (
        <div key={r.repo_name} className="heatmap-row" role="row">
          <div className="heatmap-repo-cell" role="cell" title={r.repo_name}>
            {r.repo_name.length > 22 ? `…${r.repo_name.slice(-20)}` : r.repo_name}
          </div>
          {COLS.map((c) => {
            const v = r[c.key];
            return (
              <div
                key={c.key}
                className="heatmap-cell heatmap-data"
                role="cell"
                style={{ background: cellBg(v, maxes[c.key], c.color) }}
                title={`${v} ${c.label}`}
              >
                {v > 0 ? v : <span style={{ color: "var(--fg-6)" }}>—</span>}
              </div>
            );
          })}
          <div className="heatmap-cell heatmap-data" role="cell"
               style={{ color: "var(--fg-4)" }}>
            {r.total_scans}
          </div>
        </div>
      ))}
    </div>
  );
}
