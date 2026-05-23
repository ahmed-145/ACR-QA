import { useState, useCallback, useRef } from "react";
import { Link } from "react-router-dom";
import {
  useFleet, useFleetCompliance, useStride, useRuns,
} from "@/lib/queries";
import { CountUp } from "@/components/ui/CountUp";
import { Sparkline } from "@/components/ui/Sparkline";
import { StatusBar } from "@/components/ui/StatusBar";
import { RepoHeatmap } from "@/components/charts/RepoHeatmap";
import { FindingsTrendChart } from "@/components/charts/FindingsTrendChart";
import type { FleetRepoRow } from "@/lib/api";
import {
  Shield, AlertTriangle, TrendingUp, Activity, Download,
  FileText, RefreshCw, Crosshair, Map, ChevronDown,
  Bookmark, BookmarkCheck,
} from "lucide-react";

// ── Saved views ────────────────────────────────────────────────────────────────

const LS_KEY = "acrqa:fleet:saved_views";
type SavedView = { name: string; repo: string | null; tab: string };

function loadSavedViews(): SavedView[] {
  try { return JSON.parse(localStorage.getItem(LS_KEY) || "[]"); }
  catch { return []; }
}

function persistSavedViews(views: SavedView[]) {
  localStorage.setItem(LS_KEY, JSON.stringify(views));
}

// ── CSV helpers ────────────────────────────────────────────────────────────────

function downloadCSV(rows: FleetRepoRow[]) {
  const headers = ["repo_name", "open_high", "open_med", "open_low", "regressions", "total_scans", "last_scan"];
  const lines = [
    headers.join(","),
    ...rows.map((r) =>
      headers.map((h) => JSON.stringify((r as unknown as Record<string, unknown>)[h] ?? "")).join(",")
    ),
  ];
  const blob = new Blob([lines.join("\n")], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `acrqa-fleet-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// ── STRIDE risk label ──────────────────────────────────────────────────────────

const STRIDE_COLORS: Record<string, string> = {
  Spoofing:               "var(--sev-high)",
  Tampering:              "var(--sev-high)",
  Repudiation:            "var(--sev-medium)",
  "Information Disclosure": "var(--sev-high)",
  "Denial of Service":    "var(--sev-medium)",
  "Elevation of Privilege": "var(--sev-high)",
};

// ── Compliance ring ────────────────────────────────────────────────────────────

function RiskDot({ risk }: { risk: "high" | "medium" | "none" }) {
  const colors = { high: "var(--sev-high)", medium: "var(--sev-medium)", none: "var(--fg-5)" };
  return (
    <span
      aria-label={risk}
      style={{
        display: "inline-block", width: 8, height: 8, borderRadius: "50%",
        background: colors[risk], flexShrink: 0,
      }}
    />
  );
}

// ── Outlier row ────────────────────────────────────────────────────────────────

function OutlierRow({ repo, orgAvg, onSelect }: { repo: FleetRepoRow; orgAvg: number; onSelect: () => void }) {
  const ratio = orgAvg > 0 ? repo.open_high / orgAvg : 0;
  const spike = ratio >= 2;
  return (
    <div className="fleet-outlier-row" onClick={onSelect} role="button" tabIndex={0}
         onKeyDown={(e) => e.key === "Enter" && onSelect()}>
      <span className="fleet-outlier-repo" title={repo.repo_name}>
        {repo.repo_name.length > 28 ? `…${repo.repo_name.slice(-26)}` : repo.repo_name}
      </span>
      <span className="fleet-outlier-stat" style={{ color: "var(--sev-high)" }}>
        {repo.open_high} HIGH
      </span>
      {repo.regressions > 0 && (
        <span className="fleet-badge regr">
          <TrendingUp size={10} aria-hidden /> {repo.regressions} regr
        </span>
      )}
      {spike && (
        <span className="fleet-badge spike" title={`${ratio.toFixed(1)}× org average`}>
          ×{ratio.toFixed(1)} avg
        </span>
      )}
      <span className="fleet-outlier-scans">{repo.total_scans}×</span>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────

const TABS = ["heatmap", "compliance", "trend", "stride", "export"] as const;
type Tab = typeof TABS[number];

export function FleetPage() {
  const [activeTab, setActiveTab] = useState<Tab>("heatmap");
  const [selectedRepo, setSelectedRepo] = useState<string | null>(null);
  const [savedViews, setSavedViews] = useState<SavedView[]>(loadSavedViews);
  const [showSavedMenu, setShowSavedMenu] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const { data: fleet, isLoading: fleetLoading, refetch: refetchFleet } = useFleet();
  const { data: compliance, isLoading: compLoading } = useFleetCompliance();
  const { data: strideData, isLoading: strideLoading } = useStride(
    activeTab === "stride" ? (selectedRepo ?? fleet?.repos[0]?.repo_name ?? null) : null
  );
  const { data: runsData } = useRuns(50);

  const repos = fleet?.repos ?? [];
  const org = fleet?.org;
  const completedRuns = (runsData?.runs ?? []).filter((r) => r.status === "completed");
  const repoFilteredRuns = selectedRepo
    ? completedRuns.filter((r) => r.repo_name === selectedRepo)
    : completedRuns;

  const orgAvg = repos.length > 0
    ? Math.round(repos.reduce((s, r) => s + r.open_high, 0) / repos.length)
    : 0;

  const outliers = [...repos]
    .filter((r) => r.open_high > 0 || r.regressions > 0)
    .sort((a, b) => (b.open_high + b.regressions * 3) - (a.open_high + a.regressions * 3))
    .slice(0, 8);

  const highSpark = completedRuns.slice(0, 8).reverse().map((r) => r.high_count);

  // Saved views
  const saveCurrentView = useCallback(() => {
    const name = prompt("View name:");
    if (!name) return;
    const view: SavedView = { name, repo: selectedRepo, tab: activeTab };
    const updated = [view, ...savedViews.filter((v) => v.name !== name)].slice(0, 8);
    setSavedViews(updated);
    persistSavedViews(updated);
  }, [selectedRepo, activeTab, savedViews]);

  const loadView = (v: SavedView) => {
    setSelectedRepo(v.repo);
    setActiveTab(v.tab as Tab);
    setShowSavedMenu(false);
  };

  const handleRefresh = () => {
    refetchFleet();
    setRefreshKey((k) => k + 1);
  };

  const strideRepo = selectedRepo ?? repos[0]?.repo_name ?? null;

  const printRef = useRef<HTMLDivElement>(null);

  return (
    <>
      {/* Topbar */}
      <div className="topbar no-print">
        <div className="crumbs">
          <Link to="/overview" style={{ color: "var(--fg-4)", textDecoration: "none", fontSize: 13 }}>Overview</Link>
          <span style={{ color: "var(--fg-5)", margin: "0 6px" }}>/</span>
          <span className="cur">Fleet</span>
        </div>
        <div className="grow" />
        {/* Repo filter */}
        <select
          className="fleet-repo-select"
          value={selectedRepo ?? ""}
          onChange={(e) => setSelectedRepo(e.target.value || null)}
          aria-label="Filter by repository"
        >
          <option value="">All Repos</option>
          {repos.map((r) => (
            <option key={r.repo_name} value={r.repo_name}>{r.repo_name}</option>
          ))}
        </select>
        {/* Saved views */}
        <div style={{ position: "relative" }}>
          <button
            className="btn-ghost"
            style={{ gap: 6, height: 30 }}
            onClick={() => setShowSavedMenu((v) => !v)}
            aria-label="Saved views"
          >
            <Bookmark size={13} aria-hidden />
            Views
            <ChevronDown size={11} aria-hidden />
          </button>
          {showSavedMenu && (
            <div className="fleet-saved-menu" onClick={(e) => e.stopPropagation()}>
              <button className="fleet-saved-item fleet-saved-save" onClick={saveCurrentView}>
                <BookmarkCheck size={12} aria-hidden /> Save current view
              </button>
              {savedViews.length > 0 && <div className="fleet-saved-divider" />}
              {savedViews.map((v) => (
                <button key={v.name} className="fleet-saved-item" onClick={() => loadView(v)}>
                  {v.name}
                  <span style={{ color: "var(--fg-5)", fontSize: 10.5, marginLeft: "auto" }}>{v.tab}</span>
                </button>
              ))}
              {savedViews.length === 0 && (
                <div style={{ padding: "8px 12px", fontSize: 12, color: "var(--fg-5)" }}>No saved views</div>
              )}
            </div>
          )}
        </div>
        <button className="btn-ghost" style={{ gap: 6, height: 30 }} onClick={handleRefresh} aria-label="Refresh fleet data">
          <RefreshCw size={13} aria-hidden />
        </button>
      </div>

      <div className="page-pad fleet-page" ref={printRef}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 12, marginBottom: 20 }}>
          <h1 className="title" style={{ margin: 0 }}>Fleet Posture</h1>
          {org && org.open_high > 0 && (
            <span className="fleet-alert-pill">
              <AlertTriangle size={11} aria-hidden /> {org.open_high} critical open
            </span>
          )}
        </div>

        {/* KPI strip */}
        <div className="stats" style={{ marginBottom: 20 }}>
          <div className="stat">
            <div className="lbl">Open Vulns</div>
            <div className={`num${(org?.open_total ?? 0) > 0 ? " danger" : " ok"}`}>
              <CountUp value={org?.open_total ?? 0} />
            </div>
            <div className="stat-foot">
              <span className="delta">{org?.repo_count ?? 0} repos</span>
            </div>
          </div>
          <div className="stat">
            <div className="lbl">HIGH Severity</div>
            <div className={`num${(org?.open_high ?? 0) > 0 ? " danger" : " ok"}`}>
              <CountUp value={org?.open_high ?? 0} />
            </div>
            <div className="stat-foot">
              <span className="delta">critical exposure</span>
              <Sparkline data={highSpark.length ? highSpark : [0]} color="var(--sev-high)" />
            </div>
          </div>
          <div className="stat">
            <div className="lbl">Regressions</div>
            <div className={`num${(org?.regressions ?? 0) > 0 ? " danger" : " ok"}`}>
              <CountUp value={org?.regressions ?? 0} />
            </div>
            <div className="stat-foot">
              <span className="delta">re-introduced vulns</span>
            </div>
          </div>
          <div className="stat">
            <div className="lbl">Owners w/ Open</div>
            <div className="num" style={{ color: "var(--accent-2)" }}>
              <CountUp value={org?.owners_with_open ?? 0} />
            </div>
            <div className="stat-foot">
              <span className="delta">assignees backlogged</span>
            </div>
          </div>
        </div>

        {/* Tab bar */}
        <div className="fleet-tabs no-print" role="tablist" aria-label="Fleet views">
          {TABS.map((t) => (
            <button
              key={t}
              role="tab"
              aria-selected={activeTab === t}
              className={`fleet-tab${activeTab === t ? " on" : ""}`}
              onClick={() => setActiveTab(t)}
            >
              {t === "heatmap"    && <Map size={13} aria-hidden />}
              {t === "compliance" && <Shield size={13} aria-hidden />}
              {t === "trend"      && <Activity size={13} aria-hidden />}
              {t === "stride"     && <Crosshair size={13} aria-hidden />}
              {t === "export"     && <Download size={13} aria-hidden />}
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>

        {/* ── HEATMAP TAB ──────────────────────────────────────────────── */}
        {activeTab === "heatmap" && (
          <div className="fleet-tab-body">
            <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: 16, alignItems: "start" }}>
              {/* Heatmap */}
              <div className="panel">
                <div className="panel-head">
                  <span className="panel-title">Repo Risk Heatmap</span>
                  <span className="panel-sub">open vulns by severity · click repo to drill down</span>
                </div>
                {fleetLoading ? (
                  <div className="fleet-loading">Loading…</div>
                ) : (
                  <RepoHeatmap repos={repos} />
                )}
              </div>

              {/* Outliers */}
              <div className="panel">
                <div className="panel-head">
                  <span className="panel-title">Outliers</span>
                  <span className="panel-sub">above org avg · regressions</span>
                </div>
                {outliers.length === 0 ? (
                  <div style={{ color: "var(--fg-5)", fontSize: 13, padding: "8px 0" }}>No outliers detected.</div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                    {outliers.map((r) => (
                      <OutlierRow
                        key={r.repo_name}
                        repo={r}
                        orgAvg={orgAvg}
                        onSelect={() => { setSelectedRepo(r.repo_name); setActiveTab("trend"); }}
                      />
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ── COMPLIANCE TAB ──────────────────────────────────────────── */}
        {activeTab === "compliance" && (
          <div className="fleet-tab-body">
            <div className="panel">
              <div className="panel-head">
                <span className="panel-title">OWASP Top 10 Compliance Matrix</span>
                <span className="panel-sub">open vulnerabilities mapped to controls</span>
              </div>
              {compLoading ? (
                <div className="fleet-loading">Loading…</div>
              ) : !compliance ? (
                <div style={{ color: "var(--fg-5)", fontSize: 13 }}>No data.</div>
              ) : (
                <div className="compliance-grid">
                  {compliance.matrix.map((row) => (
                    <div key={row.category} className={`compliance-cell risk-${row.risk}`}>
                      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                        <RiskDot risk={row.risk} />
                        <span className="compliance-category">{row.category}</span>
                      </div>
                      <div className="compliance-count">
                        {row.open_count > 0 ? (
                          <span style={{ color: row.risk === "high" ? "var(--sev-high)" : row.risk === "medium" ? "var(--sev-medium)" : "var(--fg-4)" }}>
                            {row.open_count} open
                          </span>
                        ) : (
                          <span style={{ color: "var(--fg-5)" }}>clean</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* CWE Top 25 stub */}
            <div className="panel" style={{ marginTop: 16 }}>
              <div className="panel-head">
                <span className="panel-title">CWE Top 25 Coverage</span>
                <span className="panel-sub">rule-to-CWE mapping summary</span>
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {[
                  { cwe: "CWE-79",  label: "XSS",          mapped: true  },
                  { cwe: "CWE-89",  label: "SQL Injection", mapped: true  },
                  { cwe: "CWE-78",  label: "OS Injection",  mapped: true  },
                  { cwe: "CWE-22",  label: "Path Traversal",mapped: true  },
                  { cwe: "CWE-502", label: "Deserialization",mapped: false },
                  { cwe: "CWE-611", label: "XXE",           mapped: false },
                  { cwe: "CWE-798", label: "Hardcoded Creds",mapped: true },
                  { cwe: "CWE-200", label: "Info Disclosure",mapped: true },
                ].map(({ cwe, label, mapped }) => (
                  <span key={cwe} className={`cwe-chip ${mapped ? "mapped" : "unmapped"}`} title={cwe}>
                    {cwe} · {label}
                  </span>
                ))}
              </div>
              <p style={{ fontSize: 11, color: "var(--fg-5)", marginTop: 12, fontFamily: "var(--mono)" }}>
                Green = detection rule mapped · Grey = coverage gap
              </p>
            </div>
          </div>
        )}

        {/* ── TREND TAB ───────────────────────────────────────────────── */}
        {activeTab === "trend" && (
          <div className="fleet-tab-body">
            <div className="panel">
              <div className="panel-head">
                <span className="panel-title">
                  Findings Trend
                  {selectedRepo && (
                    <span style={{ color: "var(--accent-2)", marginLeft: 8, fontWeight: 400 }}>
                      — {selectedRepo}
                    </span>
                  )}
                </span>
                <span className="panel-sub">
                  {selectedRepo ? `${repoFilteredRuns.length} scans` : `${completedRuns.length} scans · all repos`}
                </span>
              </div>
              <FindingsTrendChart runs={repoFilteredRuns} height={280} key={`${selectedRepo}-${refreshKey}`} />
            </div>

            {/* Per-repo KPIs when filtered */}
            {selectedRepo && (() => {
              const r = repos.find((x) => x.repo_name === selectedRepo);
              if (!r) return null;
              return (
                <div className="stats" style={{ marginTop: 16 }}>
                  {[
                    { lbl: "Open", v: r.open_vulns, color: "var(--fg-2)" },
                    { lbl: "HIGH", v: r.open_high, color: "var(--sev-high)" },
                    { lbl: "MED",  v: r.open_med, color: "var(--sev-medium)" },
                    { lbl: "LOW",  v: r.open_low, color: "var(--sev-low)" },
                    { lbl: "Regr", v: r.regressions, color: "var(--accent-2)" },
                    { lbl: "Scans", v: r.total_scans, color: "var(--fg-3)" },
                  ].map(({ lbl, v, color }) => (
                    <div key={lbl} className="stat">
                      <div className="lbl">{lbl}</div>
                      <div className="num" style={{ color }}><CountUp value={v} /></div>
                    </div>
                  ))}
                </div>
              );
            })()}
          </div>
        )}

        {/* ── STRIDE TAB ──────────────────────────────────────────────── */}
        {activeTab === "stride" && (
          <div className="fleet-tab-body">
            {/* Repo picker for STRIDE */}
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
              <Crosshair size={14} aria-hidden style={{ color: "var(--fg-4)" }} />
              <span style={{ fontSize: 12, color: "var(--fg-4)" }}>STRIDE model for:</span>
              <select
                className="fleet-repo-select"
                value={strideRepo ?? ""}
                onChange={(e) => setSelectedRepo(e.target.value || null)}
              >
                {repos.map((r) => <option key={r.repo_name} value={r.repo_name}>{r.repo_name}</option>)}
              </select>
              <button
                className="btn-ghost no-print"
                style={{ gap: 6, height: 30, marginLeft: "auto" }}
                onClick={() => window.print()}
              >
                <FileText size={13} aria-hidden /> Export PDF
              </button>
            </div>

            {strideLoading ? (
              <div className="fleet-loading">Generating STRIDE model…</div>
            ) : !strideData ? (
              <div style={{ color: "var(--fg-5)", fontSize: 13 }}>Select a repo to generate threat model.</div>
            ) : (
              <>
                <div className="stride-header">
                  <span className="stride-repo">{strideData.repo_name}</span>
                  <span className="stride-total">{strideData.total_open} open threats</span>
                </div>
                <div className="stride-grid">
                  {strideData.stride.map((row) => (
                    <div key={row.threat} className={`stride-cell risk-${row.risk}`}>
                      <div className="stride-cell-head">
                        <span className="stride-threat-label" style={{ color: STRIDE_COLORS[row.threat] ?? "var(--fg-3)" }}>
                          {row.threat.charAt(0)}
                        </span>
                        <span className="stride-threat-name">{row.threat}</span>
                        <span className="stride-count">{row.count}</span>
                      </div>
                      {row.vulns.length > 0 && (
                        <ul className="stride-vuln-list">
                          {row.vulns.slice(0, 4).map((v) => (
                            <li key={v.short_id}>
                              <span style={{ fontFamily: "var(--mono)", fontSize: 10.5, color: "var(--fg-4)" }}>{v.short_id}</span>
                              <span style={{ fontSize: 11, color: "var(--fg-3)", marginLeft: 6 }}>{v.rule}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  ))}
                </div>
                {strideData.unclassified_count > 0 && (
                  <p style={{ fontSize: 12, color: "var(--fg-5)", marginTop: 10, fontFamily: "var(--mono)" }}>
                    +{strideData.unclassified_count} unclassified finding{strideData.unclassified_count > 1 ? "s" : ""}
                  </p>
                )}
              </>
            )}
          </div>
        )}

        {/* ── EXPORT TAB ──────────────────────────────────────────────── */}
        {activeTab === "export" && (
          <div className="fleet-tab-body">
            <div className="panel">
              <div className="panel-head">
                <span className="panel-title">Board Report Export</span>
                <span className="panel-sub">posture snapshot · {new Date().toISOString().slice(0, 10)}</span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {/* CSV */}
                <div className="fleet-export-row">
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 600, color: "var(--fg-2)", marginBottom: 3 }}>Fleet Posture CSV</div>
                    <div style={{ fontSize: 12, color: "var(--fg-5)" }}>Per-repo open vulnerabilities · {repos.length} repos</div>
                  </div>
                  <button
                    className="btn-prim"
                    style={{ gap: 6 }}
                    onClick={() => downloadCSV(repos)}
                    disabled={repos.length === 0}
                  >
                    <Download size={13} aria-hidden /> Download CSV
                  </button>
                </div>

                {/* PDF */}
                <div className="fleet-export-row">
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 600, color: "var(--fg-2)", marginBottom: 3 }}>PDF Posture Report</div>
                    <div style={{ fontSize: 12, color: "var(--fg-5)" }}>Current view as browser-rendered PDF</div>
                  </div>
                  <button
                    className="btn-ghost"
                    style={{ gap: 6 }}
                    onClick={() => window.print()}
                  >
                    <FileText size={13} aria-hidden /> Print to PDF
                  </button>
                </div>

                {/* Compliance CSV */}
                <div className="fleet-export-row">
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 600, color: "var(--fg-2)", marginBottom: 3 }}>OWASP Compliance CSV</div>
                    <div style={{ fontSize: 12, color: "var(--fg-5)" }}>Open counts per control category</div>
                  </div>
                  <button
                    className="btn-ghost"
                    style={{ gap: 6 }}
                    onClick={() => {
                      if (!compliance) return;
                      const lines = ["category,open_count,risk", ...compliance.matrix.map((r) => `${r.category},${r.open_count},${r.risk}`)];
                      const blob = new Blob([lines.join("\n")], { type: "text/csv" });
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement("a");
                      a.href = url;
                      a.download = `acrqa-owasp-${new Date().toISOString().slice(0, 10)}.csv`;
                      a.click();
                      URL.revokeObjectURL(url);
                    }}
                    disabled={!compliance}
                  >
                    <Download size={13} aria-hidden /> Download CSV
                  </button>
                </div>
              </div>
            </div>

            {/* Preview table */}
            <div className="panel" style={{ marginTop: 16 }}>
              <div className="panel-head">
                <span className="panel-title">Fleet Snapshot</span>
                <span className="panel-sub">{repos.length} repositories</span>
              </div>
              <RepoHeatmap repos={repos} />
            </div>
          </div>
        )}
      </div>

      <StatusBar items={[
        { label: "Repos", value: org?.repo_count ?? 0 },
        { label: "Open Vulns", value: org?.open_total ?? 0 },
        { label: "Critical", value: org?.open_high ?? 0, color: (org?.open_high ?? 0) > 0 ? "var(--sev-high)" : undefined },
        { label: "Regressions", value: org?.regressions ?? 0, color: (org?.regressions ?? 0) > 0 ? "var(--accent-2)" : undefined },
      ]} />
    </>
  );
}
