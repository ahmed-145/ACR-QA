import { useCompliance } from "@/lib/queries";

const OWASP_LABELS: Record<string, string> = {
  A01: "Broken Access Control",
  A02: "Cryptographic Failures",
  A03: "Injection",
  A04: "Insecure Design",
  A05: "Security Misconfiguration",
  A06: "Vulnerable Components",
  A07: "Auth Failures",
  A08: "Data Integrity",
  A09: "Logging Failures",
  A10: "SSRF",
};

interface Props { runId: number; }

export function OwaspHeatmap({ runId }: Props) {
  const { data, isLoading } = useCompliance(runId);
  if (isLoading) return <div style={{ fontSize: 13, color: "var(--fg-4)" }}>Loading compliance data…</div>;
  if (!data) return null;

  const owasp = data.owasp ?? {};
  const entries = Object.keys(OWASP_LABELS).map((key) => {
    const item = owasp[key];
    const count = item?.count ?? 0;
    const severity = item?.severity ?? "none";

    // Determine risk level similar to fleet compliance matrix
    let risk: "high" | "medium" | "none" = "none";
    if (count > 0) {
      if (severity === "high") risk = "high";
      else if (severity === "medium") risk = "medium";
    }

    return {
      key,
      label: OWASP_LABELS[key],
      count,
      risk,
    };
  });

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
        <h3 style={{ margin: 0, fontSize: 13, fontWeight: 600, color: "var(--fg)" }}>OWASP Top 10 Coverage</h3>
        <span style={{ fontSize: 11, fontFamily: "var(--mono)", color: "var(--fg-4)" }}>Score: {data.overall_score ?? "—"}%</span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 8 }}>
        {entries.map(({ key, label, count, risk }) => {
          let borderColor = "var(--border)";
          let background = "var(--bg-3)";
          let countColor = "var(--fg-4)";
          let ledColor = "var(--fg-5)";

          if (count === 0) {
            borderColor = "rgba(16,185,129,0.20)";
            background = "rgba(16,185,129,0.02)";
            countColor = "var(--low)";
            ledColor = "var(--low)";
          } else if (risk === "high") {
            borderColor = "rgba(239,68,68,0.25)";
            background = "rgba(239,68,68,0.04)";
            countColor = "var(--high)";
            ledColor = "var(--high)";
          } else if (risk === "medium") {
            borderColor = "rgba(245,158,11,0.25)";
            background = "rgba(245,158,11,0.04)";
            countColor = "var(--med)";
            ledColor = "var(--med)";
          } else {
            borderColor = "rgba(96,165,250,0.20)";
            background = "rgba(96,165,250,0.02)";
            countColor = "var(--blue)";
            ledColor = "var(--blue)";
          }

          return (
            <div
              key={key}
              style={{
                borderRadius: 8,
                border: "1px solid " + borderColor,
                background: background,
                padding: "10px 12px",
                textAlign: "center",
                display: "flex",
                flexDirection: "column",
                gap: 2,
                position: "relative",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}>
                <span style={{
                  display: "inline-block", width: 6, height: 6, borderRadius: "50%",
                  background: ledColor, flexShrink: 0,
                  boxShadow: count === 0 ? "none" : "0 0 6px " + ledColor,
                }} />
                <span style={{ fontFamily: "var(--mono)", fontSize: 10.5, fontWeight: 700, color: "var(--fg-4)" }}>{key}</span>
              </div>
              <div style={{ fontSize: 11.5, color: "var(--fg-3)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={label}>
                {label}
              </div>
              <div style={{ fontSize: 18, fontWeight: 800, color: countColor, marginTop: 4, fontFamily: "var(--mono)" }}>
                {count === 0 ? "0" : count}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
