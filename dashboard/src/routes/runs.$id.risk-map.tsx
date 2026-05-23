import { useParams, useNavigate, Link } from "react-router-dom";
import { useRiskMap } from "@/lib/queries";
import { ArrowLeft, RefreshCw, AlertTriangle } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

function scoreBand(score: number): { label: string; cls: string } {
  if (score >= 75) return { label: "Critical", cls: "high" };
  if (score >= 50) return { label: "High", cls: "med" };
  if (score >= 25) return { label: "Medium", cls: "low" };
  return { label: "Low", cls: "lo" };
}

function ScoreBar({ score }: { score: number }) {
  const color =
    score >= 75 ? "var(--high)" :
    score >= 50 ? "var(--med)" :
    score >= 25 ? "#facc15" :
    "var(--low)";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ flex: 1, height: 5, borderRadius: 999, background: "rgba(255,255,255,0.05)", overflow: "hidden" }}>
        <div style={{ height: "100%", borderRadius: 999, background: color, width: `${score}%`, transition: "width 0.3s" }} />
      </div>
      <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--fg-4)", width: 28, textAlign: "right" }}>{score}</span>
    </div>
  );
}

export function RiskMapPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const runId = Number(id);
  const [refresh, setRefresh] = useState(false);
  const { data, isLoading, error, refetch } = useRiskMap(runId, refresh);

  const files = data?.files ?? [];
  const sorted = [...files].sort((a, b) => b.score - a.score);
  const topRisk = sorted.slice(0, 5);

  return (
    <>
      <div className="topbar">
        <div className="crumbs">
          <Link to="/" style={{ color: "var(--fg-4)" }}>Scans</Link>
          <span className="sep">/</span>
          <Link to={`/runs/${runId}`} style={{ color: "var(--fg-4)" }}>Run #{runId}</Link>
          <span className="sep">/</span>
          <span className="cur">Risk Map</span>
          {data && <span className="id-pill">{data.cached ? "cached" : "computed"}</span>}
        </div>
        <div className="grow" />
        <button
          className="btn-ghost"
          onClick={() => { setRefresh(true); refetch(); }}
          disabled={isLoading}
          aria-label="Refresh risk map"
        >
          <RefreshCw size={13} aria-hidden /> Refresh
        </button>
      </div>

      <div className="page-pad" style={{ maxWidth: 1100 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
          <button className="btn-icon" aria-label="Go back" onClick={() => navigate(`/runs/${runId}`)}>
            <ArrowLeft size={14} aria-hidden />
          </button>
          <div>
            <h1 className="title" style={{ margin: 0 }}>{t("runs.riskMap")}</h1>
            <p style={{ margin: 0, fontSize: 13, color: "var(--fg-4)" }}>Run #{runId} · Per-file heuristic risk scores (0–100)</p>
          </div>
        </div>

        {isLoading && (
          <div className="empty"><span className="spinner" /> Computing risk scores…</div>
        )}

        {error && (
          <div style={{ background: "rgba(239,68,68,0.08)", border: "1px solid var(--high-bdr)", borderRadius: 9, padding: "14px 18px", display: "flex", alignItems: "center", gap: 10, fontSize: 13, color: "var(--high-fg)" }}>
            <AlertTriangle size={14} aria-hidden />
            Failed to load risk map. The run may have no findings yet.
          </div>
        )}

        {data && !isLoading && (
          <>
            {/* Summary stats */}
            <div className="stats">
              {[
                { label: "Files Analyzed", value: data.total_files, danger: false },
                { label: "Critical (≥75)", value: files.filter((f) => f.score >= 75).length, danger: files.filter((f) => f.score >= 75).length > 0 },
                { label: "High (50–74)", value: files.filter((f) => f.score >= 50 && f.score < 75).length, danger: false },
                { label: "Avg Score", value: files.length ? Math.round(files.reduce((s, f) => s + f.score, 0) / files.length) : 0, danger: false },
              ].map(({ label, value, danger }) => (
                <div key={label} className="stat">
                  <div className="lbl">{label}</div>
                  <div className={`num${danger ? " danger" : ""}`}>{value}</div>
                </div>
              ))}
            </div>

            {/* Top 5 hotspots */}
            {topRisk.length > 0 && (
              <div className="panel" style={{ marginBottom: 16 }}>
                <div className="panel-head">
                  <span className="panel-title" style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <AlertTriangle size={13} style={{ color: "var(--med)" }} aria-hidden />
                    Top Risk Hotspots
                  </span>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  {topRisk.map((f) => {
                    const { label, cls } = scoreBand(f.score);
                    return (
                      <div key={f.file_path}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                          <span className={`sev ${cls}`}>{label}</span>
                          <span style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--fg-3)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1 }}>
                            {f.file_path}
                          </span>
                        </div>
                        <ScoreBar score={f.score} />
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Full file table */}
            <div className="panel" style={{ padding: 0, overflow: "hidden" }}>
              <div className="panel-head" style={{ padding: "14px 18px 12px" }}>
                <span className="panel-title">All Files</span>
                <span className="panel-sub">{files.length} files</span>
              </div>
              <div style={{ maxHeight: 600, overflowY: "auto", borderTop: "1px solid var(--border)" }}>
                {sorted.map((f) => {
                  const { label, cls } = scoreBand(f.score);
                  const toNum = (x: unknown) => (typeof x === "number" ? x : 0);
                  const topContrib = Object.entries(f.contributions ?? {})
                    .sort(([, a], [, b]) => toNum(b) - toNum(a))
                    .slice(0, 3)
                    .filter(([, v]) => toNum(v) > 0);
                  return (
                    <div key={f.file_path} style={{ padding: "12px 18px", borderBottom: "1px solid var(--border)" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                        <span className={`sev ${cls}`}>{label}</span>
                        <span style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--fg-3)", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {f.file_path}
                        </span>
                      </div>
                      <ScoreBar score={f.score} />
                      {topContrib.length > 0 && (
                        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 4 }}>
                          {topContrib.map(([k, v]) => (
                            <span key={k} style={{ fontFamily: "var(--mono)", fontSize: 10, background: "rgba(255,255,255,0.04)", border: "1px solid var(--border)", borderRadius: 4, padding: "1px 7px", color: "var(--fg-5)" }}>
                              {k}: {Number(v).toFixed(2)}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </>
        )}
      </div>
    </>
  );
}
