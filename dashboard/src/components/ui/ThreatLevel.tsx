interface ThreatLevelProps {
  highCount: number;
  className?: string;
}

function getThreat(n: number): { label: string; cls: string } {
  if (n >= 20) return { label: "CRITICAL", cls: "critical" };
  if (n >= 10) return { label: "HIGH ALERT", cls: "high-alert" };
  if (n >= 1)  return { label: "MODERATE", cls: "moderate" };
  return { label: "CLEAR", cls: "clear" };
}

export function ThreatLevel({ highCount, className }: ThreatLevelProps) {
  const { label, cls } = getThreat(highCount);
  return (
    <span
      className={`threat-pill ${cls}${className ? ` ${className}` : ""}`}
      title={`Threat level — ${highCount} HIGH finding${highCount !== 1 ? "s" : ""} in latest run`}
      aria-label={`Threat level: ${label}`}
    >
      {label}
    </span>
  );
}
