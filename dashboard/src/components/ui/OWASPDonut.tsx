interface OWASPEntry { cat: string; count: number; }

const DONUT_COLORS = [
  "#A78BFA", "#60A5FA", "#34D399", "#F59E0B", "#EF4444",
  "#EC4899", "#8B5CF6", "#06B6D4", "#84CC16", "#F97316",
];

interface OWASPDonutProps {
  data: OWASPEntry[];
  size?: number;
  showLegend?: boolean;
}

export function OWASPDonut({ data, size = 160, showLegend = true }: OWASPDonutProps) {
  const total = data.reduce((s, d) => s + d.count, 0);
  if (total === 0) return <div className="empty" style={{ padding: 32 }}>No data</div>;

  const r = size / 2;
  const innerR = r * 0.58;
  const cx = r;
  const cy = r;

  const slices: { path: string; color: string; entry: OWASPEntry }[] = [];
  let startAngle = -Math.PI / 2;

  for (let i = 0; i < data.length; i++) {
    const pct = data[i].count / total;
    const angle = pct * 2 * Math.PI;
    const endAngle = startAngle + angle;

    const x1 = cx + r * Math.cos(startAngle);
    const y1 = cy + r * Math.sin(startAngle);
    const x2 = cx + r * Math.cos(endAngle);
    const y2 = cy + r * Math.sin(endAngle);
    const ix1 = cx + innerR * Math.cos(startAngle);
    const iy1 = cy + innerR * Math.sin(startAngle);
    const ix2 = cx + innerR * Math.cos(endAngle);
    const iy2 = cy + innerR * Math.sin(endAngle);

    const large = angle > Math.PI ? 1 : 0;
    const path = [
      `M ${ix1} ${iy1}`,
      `L ${x1} ${y1}`,
      `A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`,
      `L ${ix2} ${iy2}`,
      `A ${innerR} ${innerR} 0 ${large} 0 ${ix1} ${iy1}`,
      "Z",
    ].join(" ");

    slices.push({ path, color: DONUT_COLORS[i % DONUT_COLORS.length], entry: data[i] });
    startAngle = endAngle;
  }

  return (
    <div style={{ display: "flex", alignItems: "flex-start", gap: 20, flexWrap: "wrap" }}>
      <div className="donut-wrap" style={{ width: size, height: size, flexShrink: 0 }}>
        <svg width={size} height={size} role="img" aria-label="OWASP distribution donut chart">
          {slices.map((s, i) => (
            <path key={i} d={s.path} fill={s.color} fillOpacity={0.85} stroke="var(--bg-2)" strokeWidth={1.5}>
              <title>{s.entry.cat}: {s.entry.count}</title>
            </path>
          ))}
        </svg>
        <div className="donut-center">
          <div className="n">{total}</div>
          <div className="lbl">Total</div>
        </div>
      </div>

      {showLegend && (
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 5, minWidth: 180 }}>
          {data.map((d, i) => {
            const pct = Math.round((d.count / total) * 100);
            return (
              <div key={d.cat} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ width: 8, height: 8, borderRadius: 2, background: DONUT_COLORS[i % DONUT_COLORS.length], flexShrink: 0 }} />
                <span style={{ fontSize: 11, color: "var(--fg-3)", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{d.cat}</span>
                <span style={{ fontSize: 11, color: "var(--fg-5)", fontFamily: "var(--mono)", flexShrink: 0 }}>{d.count} <span style={{ opacity: 0.5 }}>({pct}%)</span></span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
