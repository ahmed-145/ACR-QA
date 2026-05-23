import { Treemap, ResponsiveContainer, Tooltip } from "recharts";

interface Props {
  data: Record<string, { count: number; severity: string }>;
  height?: number;
}

const SEV_COLOR: Record<string, string> = {
  high:   "#ef4444",
  medium: "#f59e0b",
  low:    "#10b981",
};

interface TooltipPayload {
  payload?: { name: string; value: number; severity: string };
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayload[] }) {
  if (!active || !payload?.[0]?.payload) return null;
  const { name, value, severity } = payload[0].payload;
  return (
    <div style={{
      background: "var(--bg-3)", border: "1px solid var(--border-2)", borderRadius: 8,
      padding: "6px 10px", fontSize: 11.5, fontFamily: "var(--mono)", color: "var(--fg-2)",
    }}>
      <div style={{ fontWeight: 600, marginBottom: 2 }}>{name}</div>
      <div style={{ color: SEV_COLOR[severity?.toLowerCase()] ?? "var(--fg-4)" }}>{value} findings</div>
    </div>
  );
}

interface TreemapNodeProps {
  x?: number; y?: number; width?: number; height?: number;
  name?: string; value?: number; severity?: string;
}

function TreemapCell({ x = 0, y = 0, width = 0, height = 0, name = "", severity = "" }: TreemapNodeProps) {
  const color = SEV_COLOR[severity?.toLowerCase()] ?? "#52525b";
  if (width < 10 || height < 10) return null;
  return (
    <g>
      <rect x={x + 1} y={y + 1} width={width - 2} height={height - 2}
        fill={`${color}18`} stroke={`${color}55`} strokeWidth={1} rx={4} />
      {width > 48 && height > 22 && (
        <text x={x + 8} y={y + height / 2 + 4}
          fill={color} fontSize={10} fontFamily="var(--mono)"
          style={{ pointerEvents: "none", userSelect: "none" }}>
          {name.replace("A", "A").slice(0, 12)}
        </text>
      )}
    </g>
  );
}

export function OWASPTreemap({ data, height = 200 }: Props) {
  const nodes = Object.entries(data).map(([name, v]) => ({
    name,
    value: v.count,
    severity: v.severity,
  })).filter((d) => d.value > 0);

  if (nodes.length === 0) {
    return (
      <div style={{ height, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--fg-5)", fontSize: 12 }}>
        No OWASP data
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <Treemap
        data={nodes}
        dataKey="value"
        content={<TreemapCell />}
      >
        <Tooltip content={<CustomTooltip />} />
      </Treemap>
    </ResponsiveContainer>
  );
}
