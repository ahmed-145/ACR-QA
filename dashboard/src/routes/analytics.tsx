import { useRuns, useStats, useCompliance } from "@/lib/queries";
import { CountUp } from "@/components/ui/CountUp";
import { Sparkline } from "@/components/ui/Sparkline";
import { StatusBar } from "@/components/ui/StatusBar";
import { FindingsTrendChart } from "@/components/charts/FindingsTrendChart";
import { OWASPTreemap } from "@/components/charts/OWASPTreemap";
import { CategoryRadar } from "@/components/charts/CategoryRadar";
import { ScanCalendar } from "@/components/charts/ScanCalendar";
import { useMemo } from "react";

export function AnalyticsPage() {
  const { data: runsData } = useRuns(50);
  const runs = runsData?.runs ?? [];
  const completedRuns = runs.filter((r) => r.status === "completed");
  const runId = completedRuns[0]?.id ?? 0;
  const { data: stats } = useStats(runId);
  const { data: compliance } = useCompliance(runId);

  const totalFindings = runs.reduce((s, r) => s + r.total_findings, 0);
  const totalHigh    = runs.reduce((s, r) => s + r.high_count, 0);
  const totalMed     = runs.reduce((s, r) => s + (r.medium_count ?? 0), 0);
  const totalLow     = runs.reduce((s, r) => s + (r.low_count ?? 0), 0);
  const avgFindings  = completedRuns.length ? Math.round(totalFindings / completedRuns.length) : 0;

  const last8 = completedRuns.slice(0, 8).reverse();
  const sparkHigh  = last8.map((r) => r.high_count);
  const sparkMed   = last8.map((r) => r.medium_count ?? 0);
  const sparkLow   = last8.map((r) => r.low_count ?? 0);
  const sparkTotal = last8.map((r) => r.total_findings);

  // Real OWASP distribution for the latest completed run, served by the
  // /compliance endpoint (scripts/generate_compliance_report). Never estimated.
  const owaspTreeData = useMemo((): Record<string, { count: number; severity: string }> => {
    const results = compliance?.owasp_results ?? {};
    const out: Record<string, { count: number; severity: string }> = {};
    for (const [id, cat] of Object.entries(results)) {
      if (cat.finding_count > 0) {
        out[`${id}: ${cat.name}`] = {
          count: cat.finding_count,
          severity: cat.status === "FAIL" ? "high" : "medium",
        };
      }
    }
    return out;
  }, [compliance]);

  // Category radar derived from the same real OWASP data (top categories by count).
  const categoryRadarData = useMemo(() => {
    return Object.entries(owaspTreeData)
      .map(([name, v]) => ({ category: name.split(":")[0].trim() || name, count: v.count }))
      .filter((d) => d.count > 0)
      .sort((a, b) => b.count - a.count)
      .slice(0, 8);
  }, [owaspTreeData]);

  return (
    <>
      <div className="topbar">
        <div className="crumbs">
          <span className="cur">Analytics</span>
        </div>
      </div>

      <div className="page-pad">
        <h1 className="title">Analytics</h1>
        <p className="subtitle">Aggregate findings trends across all scans</p>

        {/* Stats with sparklines */}
        <div className="stats">
          <div className="stat">
            <div className="lbl">Total Scans</div>
            <div className="num"><CountUp value={runs.length} /></div>
            <div className="stat-foot">
              <span className="delta">{completedRuns.length} completed</span>
              <Sparkline data={sparkTotal.length ? sparkTotal : [0]} color="var(--purple)" />
            </div>
          </div>
          <div className="stat">
            <div className="lbl">Total Findings</div>
            <div className="num"><CountUp value={totalFindings} /></div>
            <div className="stat-foot">
              <span className="delta">across all runs</span>
              <Sparkline data={sparkTotal.length ? sparkTotal : [0]} color="var(--blue)" />
            </div>
          </div>
          <div className="stat">
            <div className="lbl">HIGH Severity</div>
            <div className={`num${totalHigh > 0 ? " danger" : ""}`}><CountUp value={totalHigh} /></div>
            <div className="stat-foot">
              <span className="delta">{Math.round((totalHigh / (totalFindings || 1)) * 100)}% of total</span>
              <Sparkline data={sparkHigh.length ? sparkHigh : [0]} color="var(--high)" />
            </div>
          </div>
          <div className="stat precision">
            <div className="lbl">Avg / Scan</div>
            <div className="num"><CountUp value={avgFindings} /></div>
            <div className="stat-foot">
              <span className="delta">findings/scan</span>
              <Sparkline data={sparkTotal.length ? sparkTotal : [0]} />
            </div>
          </div>
        </div>

        {/* Charts row */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
          {/* Severity breakdown */}
          <div className="panel">
            <div className="panel-head">
              <span className="panel-title">Severity Breakdown</span>
              <span className="panel-sub">{completedRuns.length} scans</span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {[
                { label: "HIGH",   count: totalHigh, color: "var(--high)", spark: sparkHigh },
                { label: "MEDIUM", count: totalMed,  color: "var(--med)",  spark: sparkMed  },
                { label: "LOW",    count: totalLow,  color: "var(--low)",  spark: sparkLow  },
              ].map(({ label, count, color, spark }) => {
                const pct = totalFindings > 0 ? Math.round((count / totalFindings) * 100) : 0;
                return (
                  <div key={label} className="risk-bar-item">
                    <div className="risk-bar-label-row">
                      <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span style={{ fontFamily: "var(--mono)", fontSize: 11, fontWeight: 700, color }}>{label}</span>
                        <Sparkline data={spark.length > 1 ? spark : [0, 0]} width={48} height={16} color={color} filled={false} />
                      </span>
                      <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--fg-4)" }}>{count} ({pct}%)</span>
                    </div>
                    <div className="risk-bar-track">
                      <div className="risk-bar-fill" style={{ width: `${pct}%`, background: color, opacity: 0.7 }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* OWASP Treemap */}
          <div className="panel">
            <div className="panel-head">
              <span className="panel-title">OWASP Distribution</span>
              <span className="panel-sub">latest scan</span>
            </div>
            <OWASPTreemap data={owaspTreeData} height={200} />
          </div>
        </div>

        {/* Trend + Radar row */}
        <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 16, marginBottom: 20 }}>
          <div className="panel">
            <div className="panel-head">
              <span className="panel-title">Findings Trend</span>
              <span className="panel-sub">last 20 scans</span>
            </div>
            <FindingsTrendChart runs={completedRuns} height={220} />
          </div>
          <div className="panel">
            <div className="panel-head">
              <span className="panel-title">Category Radar</span>
              <span className="panel-sub">OWASP categories · latest scan</span>
            </div>
            <CategoryRadar data={categoryRadarData} height={220} />
          </div>
        </div>

        {/* Scan Calendar */}
        <div className="panel" style={{ marginBottom: 20 }}>
          <div className="panel-head">
            <span className="panel-title">Scan Activity</span>
            <span className="panel-sub">26-week calendar</span>
          </div>
          <ScanCalendar runs={completedRuns} weeks={26} />
        </div>

        {/* Latest run stats */}
        {stats && (
          <div className="panel" style={{ marginBottom: 20 }}>
            <div className="panel-head">
              <span className="panel-title">Latest Run Detail</span>
              <span className="panel-sub">Run #{runId}</span>
            </div>
            <div className="signals" style={{ gridTemplateColumns: "repeat(4, 1fr)" }}>
              {[
                { lbl: "TOTAL",  v: stats.total_findings },
                { lbl: "HIGH",   v: stats.high           },
                { lbl: "MEDIUM", v: stats.medium         },
                { lbl: "LOW",    v: stats.low            },
              ].map(({ lbl, v }) => (
                <div key={lbl} className="sig">
                  <div className="lbl">{lbl}</div>
                  <div className="v"><CountUp value={v ?? 0} /></div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <StatusBar items={[
        { label: "Scans", value: runs.length },
        { label: "Findings", value: totalFindings },
        { label: "HIGH", value: totalHigh, color: totalHigh > 0 ? "var(--high)" : "var(--low)" },
      ]} />
    </>
  );
}
