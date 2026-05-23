import { useState } from "react";
import { AlertTriangle, X } from "lucide-react";
import { Link } from "react-router-dom";

interface AlertBannerProps {
  highCount: number;
  runId?: number;
}

export function AlertBanner({ highCount, runId }: AlertBannerProps) {
  const [dismissed, setDismissed] = useState(false);
  if (dismissed || highCount === 0) return null;

  return (
    <div
      role="alert"
      style={{
        background: "rgba(239,68,68,0.07)",
        borderBottom: "1px solid rgba(239,68,68,0.22)",
        padding: "9px 32px",
        display: "flex",
        alignItems: "center",
        gap: 10,
        fontSize: 12.5,
        color: "var(--high-fg)",
        fontFamily: "var(--font)",
      }}
    >
      <AlertTriangle size={13} style={{ flexShrink: 0 }} aria-hidden />
      <span style={{ flex: 1 }}>
        <strong style={{ fontWeight: 600 }}>{highCount} HIGH-severity finding{highCount !== 1 ? "s" : ""}</strong>
        {" "}detected in the latest completed run.{" "}
        {runId && (
          <Link to={`/runs/${runId}`} style={{ color: "var(--high-fg)", textDecoration: "underline", textUnderlineOffset: 3 }}>
            View run #{runId}
          </Link>
        )}
      </span>
      <button
        aria-label="Dismiss alert"
        onClick={() => setDismissed(true)}
        style={{ background: "transparent", border: "none", color: "var(--high-fg)", opacity: 0.7, cursor: "pointer", padding: 2, display: "flex" }}
      >
        <X size={13} aria-hidden />
      </button>
    </div>
  );
}
