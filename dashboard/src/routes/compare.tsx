import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useRuns } from "@/lib/queries";
import { GitCompare } from "lucide-react";
import { useTranslation } from "react-i18next";

export function ComparePage() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { data, isLoading } = useRuns(50);
  const [selectedA, setSelectedA] = useState<number | null>(null);
  const [selectedB, setSelectedB] = useState<number | null>(null);

  const runs = data?.runs ?? [];

  function handleCompare() {
    if (!selectedA || !selectedB) return;
    navigate(`/runs/${selectedA}/compare?compare=${selectedB}`);
  }

  function toggleSelect(id: number) {
    if (selectedA === id) { setSelectedA(null); return; }
    if (selectedB === id) { setSelectedB(null); return; }
    if (!selectedA) { setSelectedA(id); return; }
    if (!selectedB) { setSelectedB(id); return; }
    setSelectedA(selectedB);
    setSelectedB(id);
  }

  function selLabel(id: number) {
    if (selectedA === id) return "A";
    if (selectedB === id) return "B";
    return null;
  }

  return (
    <>
      <div className="topbar">
        <div className="crumbs">
          <Link to="/" style={{ color: "var(--fg-4)" }}>Scans</Link>
          <span className="sep">/</span>
          <span className="cur">Compare</span>
        </div>
        <div className="grow" />
        <button
          className="btn-prim"
          disabled={!selectedA || !selectedB}
          onClick={handleCompare}
          aria-label="Compare selected runs"
        >
          <GitCompare size={13} aria-hidden />
          {t("compare.compare")}
        </button>
      </div>

      <div className="page-pad" style={{ maxWidth: 860 }}>
        <h1 className="title">{t("compare.title")}</h1>
        <p className="subtitle">{t("compare.subtitle")}</p>

        {/* Selection status */}
        <div className="panel" style={{ marginBottom: 20 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 20, flexWrap: "wrap" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--fg-5)", fontWeight: 700 }}>RUN A</span>
              {selectedA ? (
                <span className="id-pill" style={{ color: "var(--purple)", borderColor: "var(--ai-bdr)" }}>#{selectedA}</span>
              ) : (
                <span style={{ fontSize: 12, color: "var(--fg-5)" }}>{t("compare.notSelected")}</span>
              )}
            </div>
            <span style={{ color: "var(--fg-5)", fontSize: 13 }}>vs</span>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--fg-5)", fontWeight: 700 }}>RUN B</span>
              {selectedB ? (
                <span className="id-pill">{selectedB}</span>
              ) : (
                <span style={{ fontSize: 12, color: "var(--fg-5)" }}>{t("compare.notSelected")}</span>
              )}
            </div>
          </div>
        </div>

        {/* Run picker */}
        {isLoading ? (
          <div className="empty"><span className="spinner" /> {t("common.loading")}</div>
        ) : runs.length === 0 ? (
          <div className="empty">{t("scans.noScansYet")}</div>
        ) : (
          <div className="panel" style={{ padding: 0, overflow: "hidden" }}>
            <div className="panel-head" style={{ padding: "14px 18px 12px" }}>
              <span className="panel-title">{t("compare.selectHint", "Click to toggle A / B selection")}</span>
            </div>
            <div style={{ borderTop: "1px solid var(--border)" }}>
              {runs.map((r) => {
                const label = selLabel(r.id);
                return (
                  <button
                    key={r.id}
                    type="button"
                    onClick={() => toggleSelect(r.id)}
                    style={{
                      width: "100%",
                      display: "grid",
                      gridTemplateColumns: "40px 1fr auto",
                      alignItems: "center",
                      gap: 12,
                      padding: "12px 18px",
                      borderBottom: "1px solid var(--border)",
                      background: label ? "rgba(167,139,250,0.06)" : "transparent",
                      cursor: "pointer",
                      textAlign: "left",
                      border: "none",
                      borderBottomColor: "var(--border)",
                      borderBottomWidth: 1,
                      borderBottomStyle: "solid",
                      transition: "background 0.1s",
                    }}
                  >
                    {label ? (
                      <span style={{
                        fontFamily: "var(--mono)", fontSize: 11, fontWeight: 700,
                        color: label === "A" ? "var(--purple)" : "var(--blue)",
                        background: label === "A" ? "var(--ai-bg)" : "rgba(96,165,250,0.08)",
                        border: `1px solid ${label === "A" ? "var(--ai-bdr)" : "rgba(96,165,250,0.3)"}`,
                        borderRadius: 5, padding: "2px 8px",
                      }}>{label}</span>
                    ) : (
                      <span style={{ width: 32, height: 22, borderRadius: 5, border: "1px dashed var(--border-2)", display: "inline-block" }} />
                    )}
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                        <span style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--fg)", fontWeight: 600 }}>#{r.id}</span>
                        <span style={{ fontSize: 13, color: "var(--fg-3)" }}>{r.repo_name}</span>
                      </div>
                      <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--fg-5)", marginTop: 2 }}>
                        {new Date(r.started_at).toLocaleString()} · {r.total_findings} findings
                      </div>
                    </div>
                    <div style={{ display: "flex", gap: 6 }}>
                      {r.high_count > 0 && <span className="sev high">{r.high_count}H</span>}
                      <span className="sev low" style={{ borderColor: "var(--border-2)", color: "var(--fg-4)", background: "rgba(255,255,255,0.04)" }}>
                        {r.status}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </>
  );
}
