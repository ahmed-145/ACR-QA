import { useQuery } from "@tanstack/react-query";
import { authHeader } from "@/lib/auth";
import { CheckCircle, XCircle, AlertTriangle } from "lucide-react";

interface ActivePolicy {
  disabled_rules: string[];
  severity_overrides: Record<string, string>;
  ignored_paths: string[];
  min_severity: string;
  quality_gate: { max_high: number; max_medium: number; max_total: number; max_security: number };
  autofix: { enabled: boolean; min_confidence: number };
  ai_explanations: { enabled: boolean; max_explanations: number };
}

interface PolicyData {
  success: boolean;
  config_file: string;
  is_valid: boolean;
  errors: string[];
  warnings: string[];
  active_policy: ActivePolicy;
  schema_keys: string[];
}

function usePolicy() {
  return useQuery({
    queryKey: ["policy"],
    queryFn: async (): Promise<PolicyData> => {
      const res = await fetch("/v1/policy", { headers: authHeader() });
      if (!res.ok) throw new Error("Failed to load policy");
      return res.json();
    },
    staleTime: 30_000,
  });
}

function Gate({ label, value, max }: { label: string; value: number | boolean | string; max?: number }) {
  const isPass = max !== undefined ? (value as number) <= max : value;
  return (
    <div style={{
      display: "flex", alignItems: "center", justifyContent: "space-between",
      padding: "10px 0", borderBottom: "1px solid var(--border)",
    }}>
      <span style={{ fontSize: 13, color: "var(--fg-2)" }}>{label}</span>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--fg-3)" }}>
          {max !== undefined ? `≤ ${max}` : String(value)}
        </span>
        {isPass
          ? <CheckCircle size={14} style={{ color: "var(--low-fg)" }} />
          : <XCircle size={14} style={{ color: "var(--high-fg)" }} />
        }
      </div>
    </div>
  );
}

export function PolicyPage() {
  const { data, isLoading, error } = usePolicy();

  return (
    <>
      <div className="topbar">
        <div className="crumbs">
          <span className="cur">Policy</span>
        </div>
      </div>

      <div className="page-pad">
        <h1 className="title">Policy Configuration</h1>
        <p className="subtitle">Active .acrqa.yml gates, overrides, and feature flags</p>

        {isLoading && <div className="empty"><span className="spinner" /> Loading policy…</div>}
        {error && <div className="empty" style={{ color: "var(--high-fg)" }}>Failed to load policy config.</div>}

        {data && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {/* Status banner */}
            <div style={{
              display: "flex", alignItems: "center", gap: 12, padding: "14px 18px",
              borderRadius: 8,
              background: data.is_valid ? "rgba(16,185,129,0.08)" : "rgba(239,68,68,0.08)",
              border: `1px solid ${data.is_valid ? "rgba(16,185,129,0.25)" : "rgba(239,68,68,0.25)"}`,
            }}>
              {data.is_valid
                ? <CheckCircle size={18} style={{ color: "var(--low-fg)", flexShrink: 0 }} />
                : <XCircle size={18} style={{ color: "var(--high-fg)", flexShrink: 0 }} />
              }
              <div>
                <div style={{ fontWeight: 600, fontSize: 14, color: data.is_valid ? "var(--low-fg)" : "var(--high-fg)" }}>
                  {data.is_valid ? "Config Valid" : "Config Invalid"}
                </div>
                <div style={{ fontSize: 12, color: "var(--fg-4)", marginTop: 2 }}>
                  {data.config_file}
                </div>
              </div>
            </div>

            {/* Errors / warnings */}
            {data.errors.length > 0 && (
              <div className="panel">
                <div className="panel-head"><span className="panel-title" style={{ color: "var(--high-fg)" }}>Errors ({data.errors.length})</span></div>
                {data.errors.map((e, i) => (
                  <div key={i} style={{ display: "flex", gap: 8, padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
                    <XCircle size={13} style={{ color: "var(--high-fg)", flexShrink: 0, marginTop: 2 }} />
                    <span style={{ fontSize: 13, color: "var(--high-fg)" }}>{e}</span>
                  </div>
                ))}
              </div>
            )}
            {data.warnings.length > 0 && (
              <div className="panel">
                <div className="panel-head"><span className="panel-title" style={{ color: "var(--med-fg)" }}>Warnings ({data.warnings.length})</span></div>
                {data.warnings.map((w, i) => (
                  <div key={i} style={{ display: "flex", gap: 8, padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
                    <AlertTriangle size={13} style={{ color: "var(--med-fg)", flexShrink: 0, marginTop: 2 }} />
                    <span style={{ fontSize: 13, color: "var(--med-fg)" }}>{w}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Quality Gates */}
            <div className="panel">
              <div className="panel-head">
                <span className="panel-title">Quality Gates</span>
                <span className="panel-sub">Build fails when thresholds exceeded</span>
              </div>
              <Gate label="Max HIGH findings" value={0} max={data.active_policy.quality_gate.max_high} />
              <Gate label="Max MEDIUM findings" value={0} max={data.active_policy.quality_gate.max_medium} />
              <Gate label="Max TOTAL findings" value={0} max={data.active_policy.quality_gate.max_total} />
              <Gate label="Max SECURITY findings" value={0} max={data.active_policy.quality_gate.max_security} />
            </div>

            {/* Feature flags */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <div className="panel">
                <div className="panel-head"><span className="panel-title">AI Explanations</span></div>
                <Gate label="Enabled" value={data.active_policy.ai_explanations.enabled} />
                <Gate label="Max per run" value={data.active_policy.ai_explanations.max_explanations} max={data.active_policy.ai_explanations.max_explanations} />
              </div>
              <div className="panel">
                <div className="panel-head"><span className="panel-title">Autofix</span></div>
                <Gate label="Enabled" value={data.active_policy.autofix.enabled} />
                <Gate label="Min confidence %" value={data.active_policy.autofix.min_confidence} max={100} />
              </div>
            </div>

            {/* Disabled rules */}
            {data.active_policy.disabled_rules.length > 0 && (
              <div className="panel">
                <div className="panel-head">
                  <span className="panel-title">Disabled Rules</span>
                  <span className="panel-sub">{data.active_policy.disabled_rules.length} rules</span>
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6, paddingTop: 8 }}>
                  {data.active_policy.disabled_rules.map((r) => (
                    <span key={r} style={{
                      fontFamily: "var(--mono)", fontSize: 11, padding: "3px 8px",
                      borderRadius: 5, background: "rgba(239,68,68,0.08)",
                      border: "1px solid rgba(239,68,68,0.2)", color: "var(--high-fg)",
                    }}>{r}</span>
                  ))}
                </div>
              </div>
            )}

            {/* Ignored paths */}
            {data.active_policy.ignored_paths.length > 0 && (
              <div className="panel">
                <div className="panel-head">
                  <span className="panel-title">Ignored Paths</span>
                  <span className="panel-sub">{data.active_policy.ignored_paths.length} paths</span>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 4, paddingTop: 8 }}>
                  {data.active_policy.ignored_paths.map((p) => (
                    <span key={p} style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--fg-4)" }}>{p}</span>
                  ))}
                </div>
              </div>
            )}

            {/* Severity overrides */}
            {Object.keys(data.active_policy.severity_overrides).length > 0 && (
              <div className="panel">
                <div className="panel-head"><span className="panel-title">Severity Overrides</span></div>
                {Object.entries(data.active_policy.severity_overrides).map(([rule, sev]) => (
                  <div key={rule} className="setting-row">
                    <span style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--fg-3)" }}>{rule}</span>
                    <span className={`sev ${sev === "high" ? "high" : sev === "medium" ? "med" : "low"}`}>{sev}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Min severity */}
            <div className="panel">
              <div className="panel-head"><span className="panel-title">Reporting</span></div>
              <div className="setting-row">
                <span style={{ fontSize: 13, color: "var(--fg-3)" }}>Minimum severity reported</span>
                <span className={`sev ${data.active_policy.min_severity === "high" ? "high" : data.active_policy.min_severity === "medium" ? "med" : "low"}`}>
                  {data.active_policy.min_severity.toUpperCase()}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
