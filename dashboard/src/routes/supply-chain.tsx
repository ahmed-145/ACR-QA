import { useState } from "react";
import { useRuns, useSupplyChain } from "@/lib/queries";
import { DependencyTree } from "@/components/supply/DependencyTree";
import { SbomDownload } from "@/components/supply/SbomDownload";
import { Package, ShieldAlert } from "lucide-react";

export function SupplyChainPage() {
  const { data: runsData, isLoading: runsLoading } = useRuns(10);
  const runs = runsData?.runs ?? [];
  const latestRun = runs.find((r) => r.status === "completed");
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);

  const runId = selectedRunId ?? latestRun?.id ?? null;
  const { data: scData, isLoading: scLoading } = useSupplyChain(runId ?? 0, { enabled: !!runId });

  const deps = scData?.dependencies ?? [];
  const highRisk = deps.filter((d) => d.risk_level === "high");
  const withCves = deps.filter((d) => d.cve_count > 0);
  const archived = deps.filter((d) => d.archived);

  return (
    <>
      <div className="topbar">
        <div className="crumbs">
          <span className="cur">Supply Chain</span>
        </div>
        <div className="grow" />
        {runId && <SbomDownload runId={runId} />}
      </div>

      <div className="page-pad">
        <h1 className="title">Supply Chain</h1>
        <p className="subtitle">Dependency risk analysis and SBOM</p>

        {/* Run selector */}
        {!runsLoading && runs.filter((r) => r.status === "completed").length > 0 && (
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 20 }}>
            {runs.filter((r) => r.status === "completed").slice(0, 8).map((r) => (
              <button
                key={r.id}
                onClick={() => setSelectedRunId(r.id)}
                className={runId === r.id ? "btn-prim" : "btn-ghost"}
                style={{ height: 28, padding: "0 12px", fontSize: 12 }}
              >
                Run #{r.id}
              </button>
            ))}
          </div>
        )}

        {scLoading || runsLoading ? (
          <div className="empty"><span className="spinner" /> Loading supply chain data…</div>
        ) : !runId ? (
          <div className="empty">
            <Package size={36} style={{ opacity: 0.3 }} aria-hidden />
            <p>No completed scans found. Run a scan first.</p>
          </div>
        ) : (
          <>
            {/* Stats */}
            <div className="stats">
              {[
                { label: "Total Dependencies", value: deps.length, danger: false },
                { label: "High Risk", value: highRisk.length, danger: highRisk.length > 0 },
                { label: "With CVEs", value: withCves.length, danger: withCves.length > 0 },
                { label: "Archived", value: archived.length, danger: archived.length > 0 },
              ].map(({ label, value, danger }) => (
                <div key={label} className="stat">
                  <div className="lbl">{label}</div>
                  <div className={`num${danger ? " danger" : ""}`}>{value}</div>
                </div>
              ))}
            </div>

            {/* Risk distribution */}
            {deps.length > 0 && (
              <div className="panel" style={{ marginBottom: 16 }}>
                <div className="panel-head">
                  <span className="panel-title">Risk Distribution</span>
                </div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  {(["high", "medium", "low"] as const).map((level) => {
                    const count = deps.filter((d) => d.risk_level === level).length;
                    return count > 0 ? (
                      <span
                        key={level}
                        className={`sev ${level === "high" ? "high" : level === "medium" ? "med" : "low"}`}
                        style={{ fontSize: 12 }}
                      >
                        {count} {level}
                      </span>
                    ) : null;
                  })}
                </div>
              </div>
            )}

            {/* High risk packages alert */}
            {highRisk.length > 0 && (
              <div style={{ background: "rgba(239,68,68,0.08)", border: "1px solid var(--high-bdr)", borderRadius: 9, padding: "14px 18px", marginBottom: 16 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, fontWeight: 600, color: "var(--high-fg)", marginBottom: 10 }}>
                  <ShieldAlert size={14} aria-hidden /> High-risk packages
                </div>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {highRisk.map((d) => (
                    <span key={d.id} style={{ fontFamily: "var(--mono)", fontSize: 11, padding: "2px 8px", borderRadius: 5, background: "rgba(239,68,68,0.10)", border: "1px solid var(--high-bdr)", color: "var(--high-fg)" }}>
                      {d.name} {d.version}{d.cve_count > 0 ? ` (${d.cve_count} CVE)` : ""}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Full tree */}
            <div className="findings-head">
              <h3>
                All Dependencies
                <span className="n">{deps.length}</span>
              </h3>
            </div>
            <DependencyTree deps={deps} />
          </>
        )}
      </div>
    </>
  );
}
