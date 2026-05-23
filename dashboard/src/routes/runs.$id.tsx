import { useParams, useNavigate, Link } from "react-router-dom";
import { useFindings, useStats, useSupplyChain, usePrRisk, useCostBenefit, useReviewBottleneck, useRunSummary, useAttestation } from "@/lib/queries";
import { FindingsTable } from "@/components/findings/FindingsTable";
import { FindingModal } from "@/components/findings/FindingModal";
import { OwaspHeatmap } from "@/components/compliance/OwaspHeatmap";
import { RiskHeatmap } from "@/components/findings/RiskHeatmap";
import { VulnerabilityTimeline } from "@/components/findings/VulnerabilityTimeline";
import { DependencyTree } from "@/components/supply/DependencyTree";
import { SbomDownload } from "@/components/supply/SbomDownload";
import { SkeletonCard } from "@/components/ui/skeleton";
import { ArrowLeft, FileDown, Map } from "lucide-react";
import { type Finding } from "@/lib/api";
import { useState } from "react";
import { useTranslation } from "react-i18next";

const TABS = ["findings", "summary", "compliance", "supply", "heatmap", "timeline", "pr-risk", "analytics", "attestation"] as const;
type Tab = typeof TABS[number];

export function RunDetailPage() {
  const { id } = useParams<{ id: string }>();
  const runId = Number(id);
  const navigate = useNavigate();
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("findings");
  const { t } = useTranslation();

  const { data: findingsData, isLoading: findingsLoading } = useFindings(runId);
  const { data: stats, isLoading: statsLoading } = useStats(runId);
  const { data: supplyChain, isLoading: scLoading } = useSupplyChain(runId);
  const { data: prRisk } = usePrRisk(runId);
  const { data: costBenefit } = useCostBenefit(runId);
  const { data: reviewBottleneck } = useReviewBottleneck(runId);
  const { data: runSummary } = useRunSummary(runId);
  const { data: attestation } = useAttestation(runId);

  const findings = findingsData?.findings ?? [];

  const sevCounts = findings.reduce(
    (acc, f) => { acc[f.severity] = (acc[f.severity] ?? 0) + 1; return acc; },
    {} as Record<string, number>
  );

  return (
    <>
      {/* Topbar */}
      <div className="topbar">
        <div className="crumbs">
          <Link to="/" className="sep" style={{ color: "var(--fg-4)" }}>Scans</Link>
          <span className="sep">/</span>
          <span className="cur">Run #{runId}</span>
          <span className="id-pill">#{runId}</span>
        </div>
        <div className="grow" />
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {(["HIGH", "MEDIUM", "LOW"] as const).map((sev) =>
            sevCounts[sev] ? (
              <span key={sev} className={`sev ${sev === "HIGH" ? "high" : sev === "MEDIUM" ? "med" : "low"}`}>
                {sevCounts[sev]} {sev}
              </span>
            ) : null
          )}
          <button className="btn-ghost" aria-label="View risk map" onClick={() => navigate(`/runs/${runId}/risk-map`)}>
            <Map size={13} aria-hidden /> Risk Map
          </button>
          <button className="btn-ghost no-print" aria-label={t("common.exportPdf")} onClick={() => window.print()}>
            <FileDown size={13} aria-hidden /> {t("common.exportPdf")}
          </button>
        </div>
      </div>

      <div className="page-pad">
        {/* Back + heading */}
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
          <button className="btn-icon" aria-label="Go back" onClick={() => navigate(-1)}>
            <ArrowLeft size={14} aria-hidden />
          </button>
          <div>
            <h1 className="title" style={{ margin: 0 }}>Run #{runId}</h1>
            <p style={{ margin: 0, fontSize: 13, color: "var(--fg-4)" }}>Detailed analysis results</p>
          </div>
        </div>

        {/* Stats */}
        {statsLoading ? (
          <div className="stats">
            {[0, 1, 2, 3].map((i) => <SkeletonCard key={i} />)}
          </div>
        ) : stats ? (
          <div className="stats">
            {[
              { label: "Total Findings", value: stats.total_findings, danger: false },
              { label: "HIGH", value: stats.high, danger: stats.high > 0 },
              { label: "MEDIUM", value: stats.medium, danger: false },
              { label: "LOW", value: stats.low, danger: false },
            ].map(({ label, value, danger }) => (
              <div key={label} className="stat">
                <div className="lbl">{label}</div>
                <div className={`num${danger ? " danger" : ""}`}>{value}</div>
              </div>
            ))}
          </div>
        ) : null}

        {/* Tabs */}
        <div className="tabs">
          {TABS.map((tab) => (
            <button key={tab} className={`tab${activeTab === tab ? " on" : ""}`} onClick={() => setActiveTab(tab)}>
              {tab === "pr-risk" ? "PR Risk" : tab === "attestation" ? "Attestation" : tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>

        {/* Tab content */}
        {activeTab === "findings" && (
          findingsLoading ? (
            <div className="empty"><span className="spinner" /> Loading findings…</div>
          ) : (
            <FindingsTable findings={findings} onSelect={setSelectedFinding} />
          )
        )}

        {activeTab === "compliance" && (
          <div className="panel">
            <OwaspHeatmap runId={runId} />
          </div>
        )}

        {activeTab === "supply" && (
          scLoading ? (
            <div className="empty"><span className="spinner" /> Loading supply chain…</div>
          ) : supplyChain ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span style={{ fontSize: 13, color: "var(--fg-4)" }}>{supplyChain.dependencies.length} dependencies analysed</span>
                <SbomDownload runId={runId} />
              </div>
              <DependencyTree deps={supplyChain.dependencies} />
            </div>
          ) : (
            <div className="empty">No supply-chain data</div>
          )
        )}

        {activeTab === "heatmap" && (
          <div className="panel">
            <RiskHeatmap runId={runId} />
          </div>
        )}

        {activeTab === "timeline" && (
          <div className="panel">
            <VulnerabilityTimeline limit={30} />
          </div>
        )}

        {activeTab === "pr-risk" && (
          prRisk ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              {/* Score banner */}
              <div className="panel">
                <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
                  <div style={{
                    fontSize: 64, fontWeight: 900, lineHeight: 1,
                    color: prRisk.band === "red" ? "var(--high)" : prRisk.band === "yellow" ? "var(--med)" : "var(--low)",
                    fontVariantNumeric: "tabular-nums",
                  }}>
                    {prRisk.score}
                  </div>
                  <div>
                    <span className={`sev ${prRisk.band === "red" ? "high" : prRisk.band === "yellow" ? "med" : "low"}`} style={{ fontSize: 12 }}>
                      {prRisk.band.toUpperCase()} RISK
                    </span>
                    <p style={{ fontSize: 12, color: "var(--fg-4)", margin: "6px 0 0" }}>Merge risk score (0 = safe, 100 = block)</p>
                  </div>
                </div>
              </div>
              {/* Contributions */}
              <div className="panel">
                <div className="panel-head"><span className="panel-title">Risk Contributions</span></div>
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {Object.entries(prRisk.contributions).map(([key, val]) => (
                    <div key={key} className="risk-bar-item">
                      <div className="risk-bar-label-row">
                        <span style={{ fontSize: 12, color: "var(--fg-3)" }}>{key.replace(/_/g, " ")}</span>
                        <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--fg-4)" }}>{((val as number) * 100).toFixed(0)}%</span>
                      </div>
                      <div className="risk-bar-track">
                        <div className="risk-bar-fill" style={{ width: `${Math.min(100, (val as number) * 100)}%`, background: "var(--purple)" }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              {prRisk.explainer.length > 0 && (
                <div className="panel">
                  <div className="panel-head"><span className="panel-title">Why this score?</span></div>
                  <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 6 }}>
                    {prRisk.explainer.map((line, i) => (
                      <li key={i} style={{ display: "flex", gap: 8, fontSize: 13, color: "var(--fg-3)" }}>
                        <span style={{ color: "var(--purple)" }}>•</span>{line}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <div className="empty"><span className="spinner" /> Loading PR risk…</div>
          )
        )}

        {activeTab === "analytics" && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            {costBenefit && (
              <div className="panel">
                <div className="panel-head"><span className="panel-title">Cost-Benefit Analysis</span></div>
                <div className="cost-row" style={{ gridTemplateColumns: "1fr 1fr", marginBottom: 0 }}>
                  {[
                    { label: "Analysis cost", value: `$${costBenefit.analysis_cost_usd.toFixed(4)}` },
                    { label: "Hours saved", value: `${costBenefit.hours_saved.toFixed(1)} h` },
                    { label: "Dev cost saved", value: `$${costBenefit.dev_cost_saved_usd.toFixed(2)}` },
                    { label: "ROI multiplier", value: String(costBenefit.roi_multiplier) },
                  ].map(({ label, value }) => (
                    <div key={label} className="cost-cell">
                      <div className="lbl">{label}</div>
                      <div className="val">{value}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {reviewBottleneck && (
              <div className="panel">
                <div className="panel-head"><span className="panel-title">Review Bottleneck</span></div>
                {[
                  { label: "Median first review", value: `${reviewBottleneck.median_time_to_first_review_hours.toFixed(1)} h` },
                  { label: "Reviewer load Gini", value: reviewBottleneck.reviewer_load_gini.toFixed(2) },
                  { label: "Merged w/o comment", value: `${(reviewBottleneck.pct_merged_without_comment * 100).toFixed(0)}%` },
                  { label: "Top-3 reviewer share", value: `${(reviewBottleneck.top3_reviewer_share * 100).toFixed(0)}%` },
                  { label: "Stale PRs", value: String(reviewBottleneck.stale_pr_count) },
                ].map(({ label, value }) => (
                  <div key={label} className="setting-row">
                    <span className="lbl">{label}</span>
                    <span className="val">{value}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === "summary" && (
          <div className="panel">
            {runSummary ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 0 }}>
                  {[
                    { lbl: "TOTAL", v: runSummary.stats.total },
                    { lbl: "HIGH",  v: runSummary.stats.high  },
                    { lbl: "MEDIUM",v: runSummary.stats.medium},
                    { lbl: "LOW",   v: runSummary.stats.low   },
                  ].map(({ lbl, v }) => (
                    <div key={lbl} className="sig">
                      <div className="lbl">{lbl}</div>
                      <div className="v">{v}</div>
                    </div>
                  ))}
                </div>
                <div style={{
                  background: "var(--bg-3)", borderRadius: 8, padding: "16px 20px",
                  fontFamily: "var(--mono)", fontSize: 12.5, color: "var(--fg-2)", lineHeight: 1.8,
                  whiteSpace: "pre-wrap", border: "1px solid var(--border)",
                }}>
                  {runSummary.summary_markdown}
                </div>
              </div>
            ) : (
              <div className="empty"><span className="spinner" /> Loading summary…</div>
            )}
          </div>
        )}

        {activeTab === "attestation" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {attestation ? (
              <>
                <div className="panel">
                  <div className="panel-head"><span className="panel-title">Provenance Attestation</span></div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                    {/* Verified banner */}
                    <div style={{
                      display: "flex", alignItems: "center", gap: 12, padding: "14px 18px",
                      borderRadius: 8, border: `1px solid ${attestation.signature_valid ? "rgba(16,185,129,0.3)" : "rgba(239,68,68,0.3)"}`,
                      background: attestation.signature_valid ? "rgba(16,185,129,0.08)" : "rgba(239,68,68,0.08)",
                    }}>
                      <span style={{ fontSize: 22 }}>{attestation.signature_valid ? "✓" : "✗"}</span>
                      <div>
                        <div style={{ fontWeight: 700, fontSize: 15, color: attestation.signature_valid ? "var(--low-fg)" : "var(--high-fg)" }}>
                          {attestation.signature_valid ? "Signature Verified" : "Signature Invalid"}
                        </div>
                        <div style={{ fontSize: 12, color: "var(--fg-4)", marginTop: 2 }}>
                          SLSA-grade cryptographic provenance for run #{runId}
                        </div>
                      </div>
                      {attestation.post_quantum && (
                        <span className="sev low" style={{ marginLeft: "auto" }}>Post-Quantum</span>
                      )}
                    </div>
                    {/* Details */}
                    {[
                      { label: "Key ID", value: attestation.key_id ?? "N/A" },
                      { label: "Created", value: attestation.created_at },
                      { label: "Algorithms", value: attestation.signature_algorithms.join(", ") || "N/A" },
                    ].map(({ label, value }) => (
                      <div key={label} className="setting-row">
                        <span style={{ fontSize: 12, color: "var(--fg-4)" }}>{label}</span>
                        <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--fg-2)" }}>{value}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="panel">
                  <div className="panel-head"><span className="panel-title">Raw Bundle</span></div>
                  <pre style={{
                    background: "var(--bg)", borderRadius: 7, padding: 16,
                    fontFamily: "var(--mono)", fontSize: 11, color: "var(--fg-3)",
                    overflow: "auto", maxHeight: 320, margin: 0,
                    border: "1px solid var(--border)",
                  }}>
                    {JSON.stringify(attestation.bundle, null, 2)}
                  </pre>
                </div>
              </>
            ) : (
              <div className="empty">No attestation found for this run.</div>
            )}
          </div>
        )}
      </div>

      {selectedFinding && (
        <FindingModal
          finding={selectedFinding}
          runId={runId}
          onClose={() => setSelectedFinding(null)}
        />
      )}
    </>
  );
}
