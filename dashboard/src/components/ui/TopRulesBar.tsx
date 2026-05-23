interface RuleEntry { rule: string; label: string; count: number; }

interface TopRulesBarProps {
  data: RuleEntry[];
  maxRows?: number;
}

export function TopRulesBar({ data, maxRows = 10 }: TopRulesBarProps) {
  const rows = data.slice(0, maxRows);
  const max = Math.max(...rows.map((r) => r.count), 1);

  return (
    <div className="chart-bar-wrap">
      {rows.map((r) => (
        <div key={r.rule} className="chart-bar-row">
          <span className="chart-bar-label" title={`${r.rule}: ${r.label}`}>
            <span style={{ color: "var(--purple)" }}>{r.rule}</span>
          </span>
          <div className="chart-bar-track">
            <div
              className="chart-bar-fill"
              style={{ width: `${(r.count / max) * 100}%`, transition: "width 0.4s ease" }}
            />
          </div>
          <span className="chart-bar-count">{r.count}</span>
        </div>
      ))}
    </div>
  );
}
