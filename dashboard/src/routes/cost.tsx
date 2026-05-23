import { useRuns } from "@/lib/queries";
import { getCostBenefit } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import type { CostBenefit } from "@/lib/api";
import { DollarSign, Clock, TrendingUp, Zap } from "lucide-react";

interface RunCost extends CostBenefit {
  run_id: number;
  repo_name: string;
  success: boolean;
}

function useCostSummary(runIds: { id: number; repo_name: string }[]) {
  return useQuery({
    queryKey: ["cost-summary", runIds.map((r) => r.id).join(",")],
    queryFn: async (): Promise<RunCost[]> => {
      const results = await Promise.allSettled(
        runIds.map((r) =>
          getCostBenefit(r.id).then((d) => ({ ...d, run_id: r.id, repo_name: r.repo_name }))
        )
      );
      return results
        .filter((r): r is PromiseFulfilledResult<RunCost> => r.status === "fulfilled" && r.value.success)
        .map((r) => r.value);
    },
    enabled: runIds.length > 0,
  });
}

export function CostPage() {
  const { data: runsData } = useRuns(20);
  const completedRuns = (runsData?.runs ?? []).filter((r) => r.status === "completed").slice(0, 10);
  const { data: costs = [], isLoading } = useCostSummary(
    completedRuns.map((r) => ({ id: r.id, repo_name: r.repo_name }))
  );

  const totalCost   = costs.reduce((s, c) => s + c.analysis_cost_usd, 0);
  const totalSaved  = costs.reduce((s, c) => s + c.dev_cost_saved_usd, 0);
  const totalHours  = costs.reduce((s, c) => s + c.hours_saved, 0);
  const totalFindings = costs.reduce((s, c) => s + c.total_findings, 0);
  const avgRoi      = costs.length ? parseFloat(costs.reduce((s, c) => s + parseFloat(c.roi_multiplier ?? "0"), 0).toFixed(1)) / costs.length : 0;

  const SUMMARY = [
    { icon: <DollarSign size={18} />, label: "Total Analysis Cost", value: `$${totalCost.toFixed(4)}`, sub: "AI explanation budget", color: "var(--purple)" },
    { icon: <TrendingUp size={18} />, label: "Developer Cost Saved", value: `$${totalSaved.toFixed(2)}`, sub: "at $100/hr equivalent", color: "var(--emerald)" },
    { icon: <Clock size={18} />, label: "Hours Saved", value: `${totalHours.toFixed(1)} h`, sub: "manual review time", color: "var(--blue)" },
    { icon: <Zap size={18} />, label: "Avg ROI", value: `${avgRoi.toFixed(1)}×`, sub: "return on analysis cost", color: "var(--med)" },
  ];

  return (
    <>
      <div className="topbar">
        <div className="crumbs">
          <span className="cur">Cost &amp; ROI</span>
        </div>
      </div>

      <div className="page-pad">
        <h1 className="title">Cost &amp; ROI</h1>
        <p className="subtitle">Economic value of automated code review across all runs</p>

        {/* Summary stats */}
        <div className="stats" style={{ gridTemplateColumns: "repeat(4, 1fr)" }}>
          {SUMMARY.map(({ icon, label, value, sub, color }) => (
            <div key={label} className="stat" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div style={{
                  width: 32, height: 32, borderRadius: 8, display: "grid", placeItems: "center",
                  background: `${color}14`, color, flexShrink: 0,
                }}>{icon}</div>
                <div className="lbl" style={{ margin: 0 }}>{label}</div>
              </div>
              <div className="num">{value}</div>
              <div style={{ fontSize: 11, color: "var(--fg-5)" }}>{sub}</div>
            </div>
          ))}
        </div>

        {/* ROI formula */}
        <div className="panel" style={{ marginBottom: 20 }}>
          <div className="panel-head">
            <span className="panel-title">How ROI Is Calculated</span>
          </div>
          <div style={{ display: "flex", gap: 24, alignItems: "center", flexWrap: "wrap", padding: "8px 0" }}>
            {[
              { label: "Findings found", value: String(totalFindings) },
              { label: "×", value: null },
              { label: "20 min/finding", value: null },
              { label: "=", value: null },
              { label: "Hours saved", value: `${totalHours.toFixed(1)} h` },
              { label: "×", value: null },
              { label: "$100/hr", value: null },
              { label: "=", value: null },
              { label: "Savings", value: `$${totalSaved.toFixed(2)}` },
            ].map(({ label, value }, i) => (
              value !== null ? (
                <div key={i} style={{ textAlign: "center" }}>
                  <div style={{ fontFamily: "var(--mono)", fontSize: 18, fontWeight: 700, color: "var(--fg)" }}>{value}</div>
                  <div style={{ fontSize: 11, color: "var(--fg-5)", marginTop: 4 }}>{label}</div>
                </div>
              ) : (
                <div key={i} style={{ fontFamily: "var(--mono)", fontSize: 20, color: "var(--fg-5)" }}>{label}</div>
              )
            ))}
          </div>
        </div>

        {/* Per-run table */}
        <div className="panel" style={{ padding: 0, overflow: "hidden" }}>
          <div className="panel-head" style={{ padding: "14px 20px" }}>
            <span className="panel-title">Per-Run Breakdown</span>
            <span className="panel-sub">{costs.length} runs analysed</span>
          </div>

          {isLoading ? (
            <div style={{ padding: 32, textAlign: "center", color: "var(--fg-4)", fontSize: 13 }}>Loading…</div>
          ) : costs.length === 0 ? (
            <div style={{ padding: 32, textAlign: "center", color: "var(--fg-5)", fontSize: 13 }}>No cost data yet. Run a scan first.</div>
          ) : (
            <>
              <div style={{
                display: "grid", gridTemplateColumns: "1fr 80px 100px 100px 80px 80px",
                padding: "8px 20px", borderBottom: "1px solid var(--border)",
                background: "var(--bg-3)",
              }}>
                {["Repo", "Run", "Cost", "Saved", "Hours", "ROI"].map((h) => (
                  <div key={h} style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--fg-5)", textTransform: "uppercase", letterSpacing: "0.08em" }}>{h}</div>
                ))}
              </div>
              {costs.map((c) => (
                <div key={c.run_id} style={{
                  display: "grid", gridTemplateColumns: "1fr 80px 100px 100px 80px 80px",
                  padding: "10px 20px", borderBottom: "1px solid var(--border)",
                }}>
                  <div style={{ fontSize: 13, color: "var(--fg-2)" }}>{c.repo_name}</div>
                  <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--fg-4)" }}>#{c.run_id}</div>
                  <div style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--fg-3)" }}>${c.analysis_cost_usd.toFixed(4)}</div>
                  <div style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--emerald)" }}>${c.dev_cost_saved_usd.toFixed(2)}</div>
                  <div style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--blue)" }}>{c.hours_saved.toFixed(1)} h</div>
                  <div style={{ fontFamily: "var(--mono)", fontSize: 12, fontWeight: 700, color: "var(--low-fg)" }}>{c.roi_multiplier}×</div>
                </div>
              ))}
            </>
          )}
        </div>
      </div>
    </>
  );
}
