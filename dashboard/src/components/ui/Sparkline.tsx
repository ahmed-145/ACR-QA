interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  filled?: boolean;
}

export function Sparkline({ data, width = 80, height = 28, color = "var(--purple)", filled = true }: SparklineProps) {
  if (!data || data.length < 2) return null;

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - ((v - min) / range) * (height - 4) - 2;
    return `${x},${y}`;
  });

  const linePath = `M ${pts.join(" L ")}`;
  const areaPath = `M ${pts[0]} L ${pts.join(" L ")} L ${width},${height} L 0,${height} Z`;

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ overflow: "visible", flexShrink: 0 }}>
      {filled && (
        <path
          d={areaPath}
          fill={color}
          fillOpacity={0.12}
          strokeWidth={0}
        />
      )}
      <path
        d={linePath}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle
        cx={pts[pts.length - 1].split(",")[0]}
        cy={pts[pts.length - 1].split(",")[1]}
        r={2.5}
        fill={color}
      />
    </svg>
  );
}
