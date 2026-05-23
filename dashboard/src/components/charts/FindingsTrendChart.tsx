import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from "recharts";
import type { Run } from "@/lib/api";

interface Props {
  runs: Run[];
  height?: number;
}

function shortDate(iso: string) {
  try {
    const d = new Date(iso);
    return `${d.getMonth() + 1}/${d.getDate()}`;
  } catch { return ""; }
}

interface TooltipPayload {
  color: string;
  name: string;
  value: number;
}

function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: TooltipPayload[]; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "var(--bg-3)", border: "1px solid var(--border-2)",
      borderRadius: 8, padding: "8px 12px", fontSize: 11.5,
      fontFamily: "var(--mono)", color: "var(--fg-2)",
      boxShadow: "0 8px 24px rgba(0,0,0,0.5)",
    }}>
      <div style={{ color: "var(--fg-4)", marginBottom: 4 }}>{label}</div>
      {payload.map((p) => (
        <div key={p.name} style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 2 }}>
          <span style={{ width: 8, height: 8, borderRadius: 2, background: p.color, display: "inline-block" }} />
          <span style={{ color: "var(--fg-3)" }}>{p.name}</span>
          <span style={{ marginLeft: "auto", color: "var(--fg)", fontWeight: 600, paddingLeft: 12 }}>{p.value}</span>
        </div>
      ))}
    </div>
  );
}

export function FindingsTrendChart({ runs, height = 220 }: Props) {
  const sorted = [...runs]
    .filter((r) => r.status === "completed")
    .sort((a, b) => a.started_at.localeCompare(b.started_at))
    .slice(-20);

  const data = sorted.map((r) => ({
    date: shortDate(r.started_at),
    HIGH: r.high_count,
    MED: r.medium_count,
    LOW: r.low_count,
  }));

  const maxHigh = Math.max(...data.map((d) => d.HIGH), 0);
  const anomalyThreshold = maxHigh * 1.5;

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 4, left: -20, bottom: 0 }}>
        <defs>
          <linearGradient id="gradHigh" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="#ef4444" stopOpacity={0.35} />
            <stop offset="95%" stopColor="#ef4444" stopOpacity={0.02} />
          </linearGradient>
          <linearGradient id="gradMed" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="#f59e0b" stopOpacity={0.30} />
            <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.02} />
          </linearGradient>
          <linearGradient id="gradLow" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="#10b981" stopOpacity={0.25} />
            <stop offset="95%" stopColor="#10b981" stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
        <XAxis dataKey="date" tick={{ fill: "var(--fg-5)", fontSize: 10, fontFamily: "var(--mono)" }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
        <YAxis tick={{ fill: "var(--fg-5)", fontSize: 10, fontFamily: "var(--mono)" }} axisLine={false} tickLine={false} allowDecimals={false} />
        <Tooltip content={<CustomTooltip />} />
        {anomalyThreshold > 0 && (
          <ReferenceLine y={anomalyThreshold} stroke="rgba(239,68,68,0.3)" strokeDasharray="4 4" label={{ value: "anomaly", fill: "rgba(239,68,68,0.5)", fontSize: 9, fontFamily: "var(--mono)" }} />
        )}
        <Area type="monotone" dataKey="LOW"  name="LOW"  stroke="#10b981" strokeWidth={1.5} fill="url(#gradLow)"  dot={false} activeDot={{ r: 3, fill: "#10b981" }} />
        <Area type="monotone" dataKey="MED"  name="MED"  stroke="#f59e0b" strokeWidth={1.5} fill="url(#gradMed)"  dot={false} activeDot={{ r: 3, fill: "#f59e0b" }} />
        <Area type="monotone" dataKey="HIGH" name="HIGH" stroke="#ef4444" strokeWidth={2}   fill="url(#gradHigh)" dot={false} activeDot={{ r: 3, fill: "#ef4444" }} />
      </AreaChart>
    </ResponsiveContainer>
  );
}
