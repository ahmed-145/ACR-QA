import type { Run } from "@/lib/api";

interface Props {
  runs: Run[];
  weeks?: number;
}

const DAY_LABELS = ["S", "M", "T", "W", "T", "F", "S"];

function startOfDay(d: Date) {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

function toKey(d: Date) {
  return startOfDay(d).getTime();
}

export function ScanCalendar({ runs, weeks = 26 }: Props) {
  const now = startOfDay(new Date());
  const totalDays = weeks * 7;
  const start = new Date(now.getTime() - (totalDays - 1) * 86400000);
  const startDayOfWeek = start.getDay();

  const countByDay: Record<number, number> = {};
  for (const r of runs) {
    if (r.status !== "completed") continue;
    try {
      const key = toKey(new Date(r.started_at));
      countByDay[key] = (countByDay[key] ?? 0) + 1;
    } catch { /* skip bad dates */ }
  }

  const maxCount = Math.max(...Object.values(countByDay), 1);

  const days: Array<{ date: Date; count: number; key: number }> = [];
  for (let i = 0; i < totalDays; i++) {
    const d = new Date(start.getTime() + i * 86400000);
    const k = toKey(d);
    days.push({ date: d, count: countByDay[k] ?? 0, key: k });
  }

  const CELL = 13;
  const GAP = 3;
  const STEP = CELL + GAP;
  const totalCols = Math.ceil((totalDays + startDayOfWeek) / 7);
  const width = totalCols * STEP;
  const height = 7 * STEP + 20;

  function cellColor(count: number) {
    if (count === 0) return "rgba(255,255,255,0.04)";
    const t = Math.min(count / maxCount, 1);
    if (t < 0.25) return "rgba(167,139,250,0.25)";
    if (t < 0.5)  return "rgba(167,139,250,0.45)";
    if (t < 0.75) return "rgba(167,139,250,0.65)";
    return "rgba(167,139,250,0.90)";
  }

  function fmt(d: Date) {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  }

  const cells: React.ReactElement[] = [];
  days.forEach(({ date, count }, i) => {
    const absDay = i + startDayOfWeek;
    const col = Math.floor(absDay / 7);
    const row = absDay % 7;
    const x = col * STEP;
    const y = row * STEP + 16;
    cells.push(
      <rect key={i} x={x} y={y} width={CELL} height={CELL} rx={2}
        fill={cellColor(count)}
        stroke={count > 0 ? "rgba(167,139,250,0.15)" : "transparent"}
        strokeWidth={0.5}
      >
        <title>{fmt(date)}{count > 0 ? ` · ${count} scan${count !== 1 ? "s" : ""}` : ""}</title>
      </rect>
    );
  });

  return (
    <div style={{ overflowX: "auto" }}>
      <svg width={width} height={height} style={{ display: "block" }}>
        {DAY_LABELS.map((l, i) => (
          <text key={i} x={-4} y={i * STEP + 16 + CELL / 2 + 3}
            textAnchor="end" fill="var(--fg-5)" fontSize={8} fontFamily="var(--mono)">
            {i % 2 === 1 ? l : ""}
          </text>
        ))}
        {cells}
      </svg>
      <div style={{ display: "flex", alignItems: "center", gap: 4, marginTop: 6, justifyContent: "flex-end" }}>
        <span style={{ fontSize: 9.5, color: "var(--fg-5)", fontFamily: "var(--mono)" }}>Less</span>
        {[0, 0.25, 0.5, 0.75, 1].map((t) => (
          <rect key={t}
            style={{ width: CELL, height: CELL, borderRadius: 2, display: "inline-block",
              background: t === 0 ? "rgba(255,255,255,0.04)" : `rgba(167,139,250,${t * 0.9})` }}
          />
        ))}
        <span style={{ fontSize: 9.5, color: "var(--fg-5)", fontFamily: "var(--mono)" }}>More</span>
      </div>
    </div>
  );
}
