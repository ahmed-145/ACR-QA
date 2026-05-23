interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  borderRadius?: number;
  style?: React.CSSProperties;
}

export function Skeleton({ width = "100%", height = 14, borderRadius = 4, style }: SkeletonProps) {
  return (
    <div
      style={{
        width,
        height,
        borderRadius,
        background: "rgba(255,255,255,0.05)",
        animation: "acr-skeleton 1.4s ease-in-out infinite",
        ...style,
      }}
    />
  );
}

export function SkeletonRow({ cols = 4 }: { cols?: number }) {
  const widths = ["40%", "60%", "30%", "20%", "50%", "35%"];
  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: `repeat(${cols}, 1fr)`,
      gap: 16,
      padding: "14px 18px",
      borderBottom: "1px solid var(--border)",
      alignItems: "center",
    }}>
      {Array.from({ length: cols }).map((_, i) => (
        <Skeleton key={i} width={widths[i % widths.length]} height={12} />
      ))}
    </div>
  );
}

export function SkeletonCard() {
  return (
    <div className="stat" style={{ gap: 12 }}>
      <Skeleton width="60%" height={10} />
      <Skeleton width="40%" height={36} />
      <Skeleton width="50%" height={10} />
    </div>
  );
}

export function SkeletonChart() {
  return (
    <div className="panel" style={{ height: 240 }}>
      <div style={{ display: "flex", alignItems: "flex-end", gap: 8, height: 180, marginTop: 24 }}>
        {[60, 80, 45, 90, 70, 55, 85].map((h, i) => (
          <Skeleton key={i} width={24} height={h} borderRadius={3} style={{ flexShrink: 0 }} />
        ))}
      </div>
    </div>
  );
}
