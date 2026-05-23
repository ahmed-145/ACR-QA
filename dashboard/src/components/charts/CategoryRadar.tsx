import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
  ResponsiveContainer, Tooltip,
} from "recharts";

interface Props {
  data: { category: string; count: number }[];
  height?: number;
}

interface TooltipPayload {
  name: string;
  value: number;
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayload[] }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "var(--bg-3)", border: "1px solid var(--border-2)", borderRadius: 8,
      padding: "6px 10px", fontSize: 11.5, fontFamily: "var(--mono)", color: "var(--fg-2)",
    }}>
      <span style={{ color: "var(--purple)" }}>{payload[0]?.value ?? 0}</span>{" findings"}
    </div>
  );
}

export function CategoryRadar({ data, height = 220 }: Props) {
  if (data.length === 0) {
    return (
      <div style={{ height, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--fg-5)", fontSize: 12 }}>
        No category data
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <RadarChart data={data} margin={{ top: 4, right: 16, bottom: 4, left: 16 }}>
        <PolarGrid stroke="rgba(255,255,255,0.06)" />
        <PolarAngleAxis
          dataKey="category"
          tick={{ fill: "var(--fg-5)", fontSize: 9.5, fontFamily: "var(--mono)" }}
        />
        <Tooltip content={<CustomTooltip />} />
        <Radar
          dataKey="count"
          stroke="#A78BFA"
          strokeWidth={1.5}
          fill="#A78BFA"
          fillOpacity={0.15}
          dot={false}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}
